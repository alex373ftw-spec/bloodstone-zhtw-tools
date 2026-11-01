import numpy as np

def decode_dxt5(buf, W, H):
    bw, bh = W//4, H//4
    nblk = bw*bh
    blocks = np.frombuffer(buf, dtype=np.uint8, count=nblk*16).reshape(nblk,16)
    a0 = blocks[:,0].astype(np.int32); a1 = blocks[:,1].astype(np.int32)
    val = np.zeros(nblk, dtype=np.uint64)
    for i in range(6):
        val |= blocks[:,2+i].astype(np.uint64) << np.uint64(8*i)
    aidx = np.zeros((nblk,16), np.uint8)
    for i in range(16):
        aidx[:,i] = ((val >> np.uint64(3*i)) & np.uint64(7)).astype(np.uint8)
    ap = np.zeros((nblk,8), np.int32)
    m = (a0 > a1)
    ap[:,0]=a0; ap[:,1]=a1
    for i in range(1,7):
        num = np.where(m, (7-i)*a0 + i*a1, (6-i)*a0 + i*a1)
        den = np.where(m, 7, 5)
        ap[:,1+i] = np.maximum(0, num//den)
    ap[:,2] = np.where(m, ap[:,2], 0)
    ap[:,6] = np.where(m, ap[:,6], 255)
    ap[:,7] = 255
    alpha = np.take_along_axis(ap, aidx.astype(np.intp), axis=1).astype(np.uint8)
    c0 = blocks[:,8].astype(np.uint16) | (blocks[:,9].astype(np.uint16)<<8)
    c1 = blocks[:,10].astype(np.uint16) | (blocks[:,11].astype(np.uint16)<<8)
    def unpack(c):
        r=((c>>11)&0x1f).astype(np.float32); g=((c>>5)&0x3f).astype(np.float32); b=(c&0x1f).astype(np.float32)
        return np.stack([r*255/31, g*255/63, b*255/31], axis=1)
    p0=unpack(c0); p1=unpack(c1)
    pal=np.zeros((nblk,4,3), np.float32)
    pal[:,0]=p0; pal[:,1]=p1
    cm=(c0>c1)
    pal[:,2]=np.where(cm[:,None],(2*p0+p1)/3,(p0+p1)/2)
    pal[:,3]=np.where(cm[:,None],(p0+2*p1)/3,0)
    cval = blocks[:,12].astype(np.uint32)|(blocks[:,13].astype(np.uint32)<<8)|(blocks[:,14].astype(np.uint32)<<16)|(blocks[:,15].astype(np.uint32)<<24)
    cidx=np.zeros((nblk,16), np.uint8)
    for i in range(16):
        cidx[:,i]=((cval>>np.uint32(2*i))&3).astype(np.uint8)
    rgb=np.take_along_axis(pal, cidx[:,:,None].astype(np.intp), axis=1).astype(np.uint8)
    img=np.zeros((H,W,4), np.uint8)
    a2 = alpha.reshape(bh, bw, 4, 4).transpose(0,2,1,3).reshape(H,W)
    r2 = rgb.reshape(bh, bw, 4, 4, 3).transpose(0,2,1,3,4).reshape(H,W,3)
    img[:,:,3]=a2; img[:,:,:3]=r2
    return img

def encode_dxt5(img, blocks_out, blk_orig, bx0, by0, bx1, by1, W, H):
    """re-encode only blocks in [bx0,bx1) x [by0,by1) block coords; keep rgb=255"""
    bw = W//4
    for by in range(by0, by1):
        for bx in range(bx0, bx1):
            blk = img[by*4:by*4+4, bx*4:bx*4+4]
            a = blk[:,:,3].reshape(16).astype(np.int32)
            # best endpoints: min/max (mode: 8 interpolated) -> use a0>a1 for 8-step mode? use a0 max
            lo = int(a.min()); hi = int(a.max())
            if hi == lo:
                a0v, a1v = lo, lo
            else:
                a0v, a1v = hi, lo   # a0>a1 -> 8 alpha values
            best = None
            for aa0, aa1 in ((a0v,a1v),(a0v,a1v-1),(min(255,a0v+1),a1v)):
                if aa0 < aa1: continue
                pal = np.zeros(8, np.int32); pal[0]=aa0; pal[1]=aa1
                if aa0 > aa1:
                    for i in range(1,7):
                        pal[i+1] = ((7-i)*aa0 + i*aa1)//7
                    pal[7]=255
                else:
                    for i in range(1,5):
                        pal[i+1] = ((5-i)*aa0 + i*aa1)//5
                    pal[5]=0; pal[6]=255; pal[7]=0
                d = np.abs(pal[None,:]-a[:,None])
                idx = d.argmin(axis=1)
                err = d[np.arange(16), idx].sum()
                if best is None or err < best[0]:
                    best = (err, aa0, aa1, idx)
            err, aa0, aa1, idx = best
            off = (by*bw+bx)*16
            blocks_out[off]=aa0; blocks_out[off+1]=aa1
            v = 0
            for i in range(16):
                v |= int(idx[i]) << (3*i)
            for i in range(6):
                blocks_out[off+2+i] = (v >> (8*i)) & 0xFF
            # RGB: solid white, 4x4 all index 0 with c0=c1=0xFFFF
            blocks_out[off+8]=0xFF; blocks_out[off+9]=0xFF
            blocks_out[off+10]=0xFF; blocks_out[off+11]=0xFF
            blocks_out[off+12]=0; blocks_out[off+13]=0; blocks_out[off+14]=0; blocks_out[off+15]=0
