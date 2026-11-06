"""Local musical estimates and explicit key relationships."""
import numpy as np
from audio_loop import features

NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def key_name(key):
    if key is None:return None
    key=key.replace(' minor','m').replace(' major','').replace('♭','b').replace('♯','#')
    for a,b in {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.items():key=key.replace(a,b)
    if key not in [n+s for n in NAMES for s in ('','m')]:raise ValueError('Unknown measured key: '+key)
    return key


def relation(theme,other):
    theme=key_name(theme);other=key_name(other)
    if not theme or not other:return 'unknown'
    if theme==other:return 'same'
    a=NAMES.index(theme.rstrip('m'));b=NAMES.index(other.rstrip('m'));am=theme.endswith('m');bm=other.endswith('m')
    if a==b and am!=bm:return 'parallel'
    if (am and not bm and (b-a)%12==3) or (not am and bm and (b-a)%12==9):return 'relative'
    if am==bm and (b-a)%12==7:return 'dominant'
    if am==bm and (b-a)%12==5:return 'subdominant'
    return 'conflict'


def measure(x):
    # 1ms RMS-onset autocorrelation; explicitly a local estimate, not Beat This!.
    n=len(x)//48;env=np.sqrt(np.mean(x[:n*48].reshape(n,48,2)**2,axis=(1,2)))
    onset=np.maximum(env-np.roll(env,1),0);onset-=onset.mean()
    size=1<<(2*len(onset)-1).bit_length();corr=np.fft.irfft(abs(np.fft.rfft(onset,size))**2,size)[:len(onset)]
    low=300;high=min(1000,len(corr)-2)
    bpm=None
    if high>low:
        lag=low+int(np.argmax(corr[low:high]));left,mid,right=corr[lag-1:lag+2]
        offset=.5*(left-right)/(left-2*mid+right) if abs(left-2*mid+right)>1e-12 else 0
        bpm=60000/(lag+np.clip(offset,-.5,.5)) if mid>1e-10 else None
    chromas=[]
    for start in range(0,len(x)-4096,2048):chromas.append(features(x[start:start+4096])[-12:])
    chroma=np.mean(chromas,axis=0) if chromas else np.zeros(12)
    profiles=[np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]),np.array([6.33,2.68,3.52,5.38,2.6,3.53,2.54,4.75,3.98,2.69,3.34,3.17])]
    ranked=sorted([(float(np.corrcoef(chroma,np.roll(p,i))[0,1]),NAMES[i]+('m' if j else '')) for j,p in enumerate(profiles) for i in range(12)],reverse=True)
    confidence=ranked[0][0]-ranked[1][0]
    return dict(bpm=float(bpm) if bpm is not None else None,key=ranked[0][1] if np.isfinite(ranked[0][0]) else None,key_source='local_estimate',
        key_confidence_margin=confidence,method='1ms RMS periodicity; chroma profile correlation',
        downbeat=None,downbeat_reason='Requires provided bar_position or Beat This!; onset is not a downbeat')

