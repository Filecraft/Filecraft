package com.prepare.app;

import java.io.*;
import java.security.*;
import java.util.Arrays;

/** Bounded streaming copy and exact read-back verification; callers own streams. */
public final class Copy {
    private Copy() { }
    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch(NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }
    public static byte[] transfer(InputStream in,OutputStream out,long expected,Policy.Token token) throws IOException {
        MessageDigest digest=digest(); long count=0;
        byte[] buffer=new byte[32768]; int n;
        token.check();
        while((n=in.read(buffer))!=-1) {
            token.check(); count+=n;
            if(count>expected) throw new IOException("Source size changed");
            out.write(buffer,0,n); digest.update(buffer,0,n);
        }
        token.check();
        if(count!=expected) throw new IOException("Source truncated");
        return digest.digest();
    }
    public static void verify(InputStream in,long expected,byte[] hash,Policy.Token token) throws IOException {
        MessageDigest digest=digest(); long count=0;
        byte[] buffer=new byte[32768]; int n;
        token.check();
        while((n=in.read(buffer))!=-1) {
            token.check(); count+=n;
            if(count>expected) throw new IOException("Destination larger than expected");
            digest.update(buffer,0,n);
        }
        token.check();
        if(count!=expected || !Arrays.equals(hash,digest.digest())) throw new IOException("Destination verification failed");
    }
}
