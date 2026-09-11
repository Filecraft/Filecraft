package com.prepare.app;

import java.io.*;
import java.math.BigDecimal;

public final class Policy {
    private Policy() { }
    public static final int MAX_PAGES=20;
    public static final class Cancelled extends IOException {
        public Cancelled() { super("Operation cancelled."); }
    }
    public static final class TooLarge extends IOException {
        public TooLarge() { super("Cannot fit the byte limit at the supported resolutions. Try fewer images or a larger limit."); }
    }
    public static final class Token {
        private volatile boolean cancelled;
        public void cancel() { cancelled=true; }
        public void check() throws Cancelled { if(cancelled || Thread.currentThread().isInterrupted()) throw new Cancelled(); }
    }
    public static long limitBytes(String mb) {
        try {
            long bytes=new BigDecimal(mb.trim()).multiply(new BigDecimal("1000000")).longValueExact();
            if(bytes<1 || bytes>100000000) throw new IllegalArgumentException();
            return bytes;
        } catch(ArithmeticException | NumberFormatException e) {
            throw new IllegalArgumentException("Enter a byte limit greater than 0 and at most 100 MB.");
        }
    }
    /** Reject before writing excess bytes; never silently truncate a PDF. */
    public static final class LimitedOutput extends FilterOutputStream {
        private final long limit; private long count; private final Token token;
        public LimitedOutput(OutputStream out,long limit,Token token) { super(out); this.limit=limit; this.token=token; }
        private void reserve(int n) throws IOException {
            token.check(); if(n>limit-count) throw new TooLarge(); count+=n;
        }
        @Override public void write(int b) throws IOException { reserve(1); out.write(b); }
        @Override public void write(byte[] b,int offset,int length) throws IOException {
            if(offset<0 || length<0 || offset>b.length-length) throw new IndexOutOfBoundsException();
            reserve(length); out.write(b,offset,length);
        }
    }
}
