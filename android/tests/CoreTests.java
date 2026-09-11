package com.prepare.app;
public final class CoreTests {
    private static void near(double a, double b) {
        if (Math.abs(a-b) > 0.001) throw new AssertionError(a + " != " + b);
    }
    public static void main(String[] args) {
        Geometry g = Geometry.fit(400, 200, Geometry.Layout.A4, 18);
        near(g.pageWidth,595); near(g.pageHeight,842);
        near(g.width,559); near(g.height,279.5);
        near(g.left,18); near(g.top,(842-279.5)/2);
        System.out.println("PASS A4 centered aspect-fit geometry");
        near(Geometry.fit(10,20,Geometry.Layout.LETTER,0).pageWidth,612);
        Geometry original=Geometry.fit(4000,2000,Geometry.Layout.ORIGINAL,12);
        near(original.pageWidth,2024); near(original.pageHeight,1024);
        try { Geometry.fit(0,10,Geometry.Layout.A4,0); throw new AssertionError(); }
        catch (IllegalArgumentException expected) { }
        System.out.println("PASS Letter, original, invalid geometry");
        try {
            java.io.ByteArrayOutputStream bytes=new java.io.ByteArrayOutputStream();
            Policy.Token token=new Policy.Token();
            Policy.LimitedOutput out=new Policy.LimitedOutput(bytes,3,token);
            out.write(new byte[]{1,2,3});
            try { out.write(4); throw new AssertionError("limit not enforced"); }
            catch (Policy.TooLarge expected) { }
            if(bytes.size()!=3) throw new AssertionError("overflow written");
            token.cancel();
            try { token.check(); throw new AssertionError("cancellation ignored"); }
            catch (Policy.Cancelled expected) { }
            try { Policy.limitBytes("0"); throw new AssertionError(); }
            catch (IllegalArgumentException expected) { }
            if(Policy.limitBytes("1.5")!=1500000) throw new AssertionError();
            System.out.println("PASS exact byte cap, cancellation, decimal MB validation");
            byte[] payload=new byte[]{10,20,30,40};
            java.io.ByteArrayOutputStream destination=new java.io.ByteArrayOutputStream();
            Policy.Token copyToken=new Policy.Token();
            byte[] digest=Copy.transfer(new java.io.ByteArrayInputStream(payload),destination,4,copyToken);
            Copy.verify(new java.io.ByteArrayInputStream(destination.toByteArray()),4,digest,copyToken);
            try { Copy.verify(new java.io.ByteArrayInputStream(new byte[]{10,20,30,41}),4,digest,copyToken); throw new AssertionError("corruption accepted"); }
            catch(java.io.IOException expected) { }
            try { Copy.verify(new java.io.ByteArrayInputStream(new byte[]{10,20}),4,digest,copyToken); throw new AssertionError("truncation accepted"); }
            catch(java.io.IOException expected) { }
            copyToken.cancel();
            try { Copy.transfer(new java.io.ByteArrayInputStream(payload),new java.io.ByteArrayOutputStream(),4,copyToken); throw new AssertionError("copy cancellation ignored"); }
            catch(Policy.Cancelled expected) { }
            System.out.println("PASS copy digest verification, corruption, truncation, cancellation");
        } catch (java.io.IOException e) { throw new AssertionError(e); }
    }
}
