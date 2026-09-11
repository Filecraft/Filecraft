package com.prepare.app;

/** PDF points; aspect-fit never crops. Original uses one pixel per point, capped at 2000. */
public final class Geometry {
    public enum Layout { A4, ORIGINAL, LETTER }
    public final int pageWidth, pageHeight;
    public final float left, top, width, height;
    private Geometry(int pw, int ph, float l, float t, float w, float h) {
        pageWidth=pw; pageHeight=ph; left=l; top=t; width=w; height=h;
    }
    public static Geometry fit(int iw, int ih, Layout layout, int margin) {
        if (iw<=0 || ih<=0 || layout==null || margin<0 || margin>72)
            throw new IllegalArgumentException("Invalid image size, layout or margin");
        int pw=595, ph=842;
        if (layout==Layout.LETTER) { pw=612; ph=792; }
        if (layout==Layout.ORIGINAL) {
            double scale=Math.min(1.0,2000.0/Math.max(iw,ih));
            pw=(int)Math.ceil(iw*scale)+2*margin;
            ph=(int)Math.ceil(ih*scale)+2*margin;
        }
        double scale=Math.min((pw-2.0*margin)/iw,(ph-2.0*margin)/ih);
        float w=(float)(iw*scale), h=(float)(ih*scale);
        return new Geometry(pw,ph,(pw-w)/2,(ph-h)/2,w,h);
    }
}
