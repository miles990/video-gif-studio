"""Dense band refinement, minimum-cost graph cut and independent ghost checks."""
import cv2
import numpy as np

def gray(a):return cv2.cvtColor(a[...,:3],cv2.COLOR_RGB2GRAY)

def band_residual(a,b,band):
    points=cv2.goodFeaturesToTrack(gray(a),800,.01,4,mask=band.astype('uint8')*255)
    if points is None or len(points)<8:return None
    params=dict(winSize=(15,15),maxLevel=2,criteria=(3,40,.001))
    moved,ok,_=cv2.calcOpticalFlowPyrLK(gray(a),gray(b),points,None,**params)
    back,ok2,_=cv2.calcOpticalFlowPyrLK(gray(b),gray(a),moved,None,**params)
    good=(ok.ravel()>0)&(ok2.ravel()>0)&(np.linalg.norm((back-points).reshape(-1,2),axis=1)<=1)
    if good.sum()<8:return None
    residual=np.linalg.norm((moved-points).reshape(-1,2),axis=1)[good]
    return dict(residual_px=float(np.median(residual)),residual_p95_px=float(np.percentile(residual,95)),residual_points=int(good.sum()),residual_method='independent_band_forward_backward_LK')

def refine_band(a,b,mask,margin):
    # Include unchanged context on both sides of the eventual seam, but never
    # use a flow fit's own displacement as proof of its remaining error.
    width=max(12,margin*2)
    outer=cv2.dilate(mask,np.ones((2*width+1,2*width+1),np.uint8))>0
    inner=cv2.erode(mask,np.ones((7,7),np.uint8))>0
    band=outer&~inner
    flow=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(gray(a),gray(b),None)
    reverse=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(gray(b),gray(a),None)
    y,x=np.indices(mask.shape,dtype='float32');mx=x+flow[...,0];my=y+flow[...,1]
    reverse_at=cv2.remap(reverse,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    consistent=(np.linalg.norm(flow+reverse_at,axis=2)<=1)&(np.linalg.norm(flow,axis=2)<=width)
    warped=cv2.remap(b,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    valid=band&consistent
    result=b.copy();result[valid]=warped[valid]
    before=band_residual(a,b,band);after=band_residual(a,result,band)
    # Reject a refinement that makes independently measured correspondences worse.
    accepted=after is not None and (before is None or after['residual_px']<=before['residual_px'])
    if not accepted:result=b;after=before
    return result,band,dict(method='cv2_DIS',accepted=accepted,consistent_fraction=float(consistent[band].mean()) if band.any() else 0,
                            before=before,after=after)

def graphcut_weights(a,b,mask,expanded,feather):
    """Photomontage cut: hard inner/outer seeds, |A-B| cost in the margin.

    OpenCV's graph-cut seam finder minimizes colour mismatch over the overlap.
    Only the margin is shared: original owns exterior, regeneration owns mask.
    """
    original_mask=np.where(mask>0,0,255).astype('uint8')
    generated_mask=expanded.copy()
    masks=[cv2.UMat(original_mask),cv2.UMat(generated_mask)]
    finder=cv2.detail_GraphCutSeamFinder('COST_COLOR')
    finder.find([a[...,:3].astype('float32'),b[...,:3].astype('float32')],[(0,0),(0,0)],masks)
    chosen=(masks[1].get()>0)&(expanded>0);chosen[mask>0]=True
    width=min(3,feather)
    if width:
        # Feather only inward from the selected seam, leaving exterior exact.
        distance=cv2.distanceTransform(chosen.astype('uint8'),cv2.DIST_L2,5)
        weights=np.clip(distance/width,0,1)
        weights=weights*weights*(3-2*weights)
    else:weights=chosen.astype('float32')
    weights[mask>0]=1;weights[expanded==0]=0
    return weights,dict(method='minimum_cost_graph_cut_color',feather_px=width,selected_pixels=int(chosen.sum()))

def ghosting(a,b,band,weights=None):
    """Offset paired contours indicate doubled spines/stems in a blend band.

    Count reciprocal nearest-edge distances >1 px (acceptance bound), <=8 px
    (local ghost rather than unrelated content). Report raw evidence as well.
    """
    ea=cv2.Canny(gray(a),60,120)>0;eb=cv2.Canny(gray(b),60,120)>0
    da=cv2.distanceTransform((~ea).astype('uint8'),cv2.DIST_L2,5)
    db=cv2.distanceTransform((~eb).astype('uint8'),cv2.DIST_L2,5)
    support=band.copy()
    if weights is not None:
        seam=(weights>0)&(weights<1)
        support &= cv2.dilate(seam.astype('uint8'),np.ones((9,9),np.uint8))>0
    left=db[ea&support];right=da[eb&support]
    nleft=int(np.sum((left>1)&(left<=8)));nright=int(np.sum((right>1)&(right<=8)))
    fractions=[nleft/max(len(left),1),nright/max(len(right),1)]
    flagged=min(nleft,nright)>=8 and min(fractions)>=.10
    return dict(flagged=bool(flagged),offset_edge_pixels=[nleft,nright],edge_pixels=[len(left),len(right)],
                offset_fractions=fractions,offset_range_px=[1,8],minimum_pairs=8,minimum_fraction=.10,
                method='reciprocal_offset_edges_in_seam_band')
