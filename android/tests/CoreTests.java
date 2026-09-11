package com.prepare.app;
public final class CoreTests {
    private static void near(double a, double b) {
        if (Math.abs(a-b) > 0.001) throw new AssertionError(a + " != " + b);
    }
    private static void swallowedWriteFailure(String kind, int overload) throws java.io.IOException {
        java.io.ByteArrayOutputStream prefix=new java.io.ByteArrayOutputStream();
        java.io.IOException disk=new java.io.IOException("synthetic disk failure");
        java.io.OutputStream sink=new java.io.OutputStream() {
            boolean failed;
            public void write(int b) throws java.io.IOException {
                if(kind.equals("disk") && !failed && prefix.size()==2) { failed=true; throw disk; }
                prefix.write(b);
            }
        };
        Policy.Token token=new Policy.Token();
        Policy.LimitedOutput out=new Policy.LimitedOutput(sink,kind.equals("cap")?3:100,token);
        out.write(new byte[]{1,2});
        if(kind.equals("cancel")) token.cancel();
        java.io.IOException original=null;
        // Model native PdfDocument swallowing a callback exception and returning normally.
        try {
            if(overload==0) { out.write(3); out.write(4); }
            else if(overload==1) out.write(new byte[]{3,4});
            else out.write(new byte[]{0,3,4,0},1,2);
        } catch(java.io.IOException swallowed) { original=swallowed; }
        if(original==null) throw new AssertionError("fixture did not fail: "+kind);
        if(kind.equals("disk") && original!=disk) throw new AssertionError("I/O identity lost");
        int size=prefix.size();
        try { out.checkFailure(); throw new AssertionError("native completion accepted "+kind); }
        catch(java.io.IOException latched) { if(latched!=original) throw new AssertionError("completion failure replaced"); }
        try { out.flush(); throw new AssertionError("swallowed "+kind+" accepted (overload "+overload+")"); }
        catch(java.io.IOException latched) { if(latched!=original) throw new AssertionError("first failure lost"); }
        try { out.write(9); throw new AssertionError("write after failure accepted"); }
        catch(java.io.IOException latched) { if(latched!=original) throw new AssertionError("failure replaced"); }
        if(prefix.size()!=size || size==0) throw new AssertionError("prefix altered after failure");
    }
    public static void main(String[] args) {
        try {
            for(String kind:new String[]{"cap","cancel","disk"})
                for(int overload=0;overload<3;overload++) swallowedWriteFailure(kind,overload);
            // A partial delegate write must poison the stream even when it later recovers.
            java.io.IOException disk=new java.io.IOException("partial disk write");
            java.io.ByteArrayOutputStream prefix=new java.io.ByteArrayOutputStream();
            java.io.OutputStream sink=new java.io.OutputStream() {
                public void write(int b) { prefix.write(b); }
                public void write(byte[] b,int offset,int length) throws java.io.IOException {
                    prefix.write(b[offset]); throw disk;
                }
            };
            Policy.LimitedOutput partial=new Policy.LimitedOutput(sink,100,new Policy.Token());
            try { partial.write(new byte[]{1,2,3}); } catch(java.io.IOException swallowed) { }
            try { partial.checkFailure(); throw new AssertionError("partial disk write accepted"); }
            catch(java.io.IOException expected) { if(expected!=disk) throw new AssertionError("disk failure reclassified"); }
            if(prefix.size()!=1) throw new AssertionError("partial fixture failed");
            boolean[] closed={false};
            Policy.LimitedOutput cap=new Policy.LimitedOutput(new java.io.ByteArrayOutputStream() {
                public void close() { closed[0]=true; }
            },1,new Policy.Token());
            try(Policy.LimitedOutput resource=cap) {
                try { resource.write(new byte[]{1,2}); } catch(Policy.TooLarge swallowed) { }
                resource.checkFailure();
                throw new AssertionError("cap accepted at completion");
            } catch(Policy.TooLarge expected) { }
            if(!closed[0]) throw new AssertionError("latched failure leaked sink");
            System.out.println("PASS swallowed cap/cancellation/disk errors, partial writes, failure identity and close cleanup");
        } catch(java.io.IOException e) { throw new AssertionError(e); }

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
