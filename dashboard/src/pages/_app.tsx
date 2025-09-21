import type { AppProps } from 'next/app';
import Head from 'next/head';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>PAKE System - Enterprise Knowledge Management Platform</title>
        <meta name="description" content="Enterprise-grade AI-powered knowledge engineering platform with multi-source ingestion, real-time trend intelligence, and advanced analytics." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
        <meta name="theme-color" content="#1f2937" />
        <meta property="og:title" content="PAKE System - Enterprise Knowledge Management" />
        <meta property="og:description" content="Production-ready AI research platform with sub-second multi-source ingestion" />
        <meta property="og:type" content="website" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <Component {...pageProps} />
    </>
  );
}