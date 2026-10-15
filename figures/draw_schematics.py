"""Draw the manuscript schematics directly as font-embedded vector PDFs.

Run: python figures/draw_schematics.py --output figures
Requires Python 3.9+ and Matplotlib. No TeX engine or network is used.
The diagrams express the defined model; they are not measurement plots.
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def draw(out):
    d=Drawing((-1.6,-4.7,7.7,.85))
    for name,x,y,label in [('src',0,0,'complete\nBFIL-1 source'),
        ('prod',3.1,0,'untrusted\nproducer'),('ev',6.2,0,'IR + ledger\nprogram + proofs'),
        ('chk',3.1,-2.8,'independent\nchecker'),('out',6.2,-2.8,'accepted\nclassification')]:d.box(name,x,y,2.5,1.1,label)
    d.edge('src','prod','e','w');d.edge('prod','ev','e','w')
    d.edge('ev','chk','s','n',via=[(6.2,-1.35),(3.1,-1.35)])
    d.edge('chk','out','e','w');d.edge('src','chk','s','w',via=[(0,-2.8)])
    d.text(.25,-1.7,'reconstruct all\nobligations',size=8.5,ha='left')
    d.frame(-1.32,-.62,2.64,1.24)
    d.text(3.1,-4.0,'parser/type model + semantics (TCB)',size=8.5)
    d.save(out,'architecture')

    d=Drawing((-1.3,-1.75,5.35,1.4))
    for name,x,y,label in [('lo',0,0,r'$\mathcal{L}(P^-)$'),
        ('u',2,.6,r'$\mathcal{L}(P_{\{u\}})$'),('v',2,-.6,r'$\mathcal{L}(P_{\{v\}})$'),
        ('hi',4,0,r'$\mathcal{L}(P^+)$')]:d.box(name,x,y,1.5,.55,label,size=8.5)
    for a,b,sa,sb in [('lo','u','ne','w'),('lo','v','e','w'),('u','hi','e','nw'),('v','hi','e','w')]:d.edge(a,b,sa,sb)
    d.text(0,.83,'empty\ncompletion',size=8.5)
    d.text(4,.83,'all-enabled\ncompletion',size=8.5)
    d.text(2,-1.4,r'$q\in\mathcal{L}(P^+)\setminus\mathcal{L}(P^-)\Rightarrow\mathrm{unresolved}$',size=8.5)
    d.save(out,'completions')

    d=Drawing((-1.0,-1.15,3.75,1.8))
    d.box('s1',0,.975,1.15,.5,r'$s_1:a\to b$',size=8.5)
    d.box('s2',0,0,1.15,.5,r'$s_2:a\to q$',size=8.5)
    for name,x,y in [('a',1.681,.975),('b',3.034,.975),('q',3.034,0)]:
        d.box(name,x,y,.58,.58,'$'+name+'$',shape='circle',size=8.5)
    d.edge('s1','a','e','w');d.edge('a','b','e','w');d.edge('s2','q','e','w',dashed=True)
    d.line([(1.328,.64),(3.387,.64),(3.387,1.31),(1.328,1.31),(1.328,.64)])
    d.text(2.354,1.62,r'old proof $C=\{a,b\}$',size=8.5)
    d.text(1.845,-.78,'omitted by\ntranslator',size=8.5)
    d.arrow((1.845,-.42),(2.419,0),dashed=True)
    d.save(out,'omission')

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
    output=parser.parse_args().output
    output.mkdir(parents=True,exist_ok=True)
    draw(output)
