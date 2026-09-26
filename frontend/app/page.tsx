import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import BrandLogo from "@/components/branding/BrandLogo";
import styles from "./landing.module.css";

export const metadata: Metadata = {
  title: "SnapTracer — A better way to share every event photo",
  description: "Stop sending event photos one by one. Upload once and let every guest find their own photos privately.",
};

const steps = [
  ["01", "Create your event", "Set up a space for your trip, wedding, party, or fest.", "✳"],
  ["02", "Share the event QR", "Guests register with a photo and email.", "⌗"],
  ["03", "Add your photos", "Bulk upload or paste a public Google Drive link.", "↥"],
  ["04", "Notify guests", "When photos are ready, notify everyone in one tap.", "↗"],
  ["05", "Download from email", "Guests open their email link and download in one tap.", "↓"],
];

const faqs = [
  ["Do I have to sort the photos first?", "No. Upload the event photos together. SnapTracer helps match each registered guest with photos they appear in."],
  ["How do guests find their photos?", "Share the event QR or link. Guests register with a selfie, then open their private photo gallery."],
  ["Can I use it for more than trips?", "Yes. It works for weddings, parties, college events, conferences, and any occasion with lots of people and photos."],
  ["How long are photos kept?", "Uploaded photos and guest selfies are scheduled for deletion 45 days after upload. You can purge event media earlier from the dashboard."],
];

export default function Home() {
  return <main className={styles.page}>
    <div className={styles.announcement}><b>✳</b> Made for the moments everyone wants back <span>↗</span></div>
    <header className={styles.header}>
      <BrandLogo href="/" />
      <nav aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#moments">Who it&apos;s for</a><a href="#questions">FAQs</a></nav>
      <div className={styles.headerActions}><Link href="/login">Log in</Link><Link className={styles.headerCta} href="/register">Create an event ↗</Link></div>
    </header>
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroCopy}>
        <p className={styles.eyebrow}>— THE AFTER-PARTY, SORTED</p>
        <h1 id="hero-title">Great trip.<br />A thousand photos.<br /><em>One tired iPhone guy.</em></h1>
        <p className={styles.lead}>You took the photos. Now everyone wants theirs. Upload them once to SnapTracer and let every person find their own moments.</p>
        <div className={styles.heroActions}><Link className={styles.primaryButton} href="/register">Create your event <span>↗</span></Link><a href="#how-it-works">See how it works ↓</a></div>
        <p className={styles.footnote}><b>✳ ✳ ✳</b> One link for everyone. Their photos, in one place.</p>
      </div>
      <div className={styles.heroVisual}>
        <div className={styles.heroPhoto}><Image src="/trip-friends.png" alt="Friends taking a group selfie on a mountain trip" fill priority sizes="(max-width: 800px) 100vw, 52vw" /></div>
        <div className={`${styles.bubble} ${styles.bubbleOne}`}>💬 Bhai meri photo bhej na yaar</div>
        <div className={`${styles.bubble} ${styles.bubbleTwo}`}>📸 iPhone wale, file bana ke bhej!</div>
        <div className={`${styles.bubble} ${styles.bubbleThree}`}>⏰ Jaldi bhej de pleaseee</div>
        <div className={styles.sticker}><strong>86</strong><small>new messages</small></div>
        <span className={styles.caption}>EVERY GROUP TRIP. EVERY SINGLE TIME.</span>
      </div>
    </section>
    <div className={styles.ticker}><div>UPLOAD ONCE <b>✳</b> SHARE ONE LINK <b>✳</b> EVERYONE FINDS THEIR PHOTOS <b>✳</b> UPLOAD ONCE <b>✳</b> SHARE ONE LINK <b>✳</b> EVERYONE FINDS THEIR PHOTOS <b>✳</b></div></div>
    <section className={styles.problem} aria-labelledby="problem-title">
      <p className={styles.label}>SOUND FAMILIAR?</p><h2 id="problem-title">The photos are amazing.<br /><em>The sharing is a mess.</em></h2>
      <div className={styles.problemGrid}>
        <article className={styles.problemCard}><small>01 / THE GROUP CHAT</small><div className={styles.messages}><span>“Meri solo wali?”</span><span>“Original quality mein bhejo!”</span><span>“Mere photos kidhar hain?”</span></div><p>Your camera roll becomes everyone&apos;s to-do list.</p></article>
        <article className={styles.solutionCard}><small>02 / THE BETTER WAY</small><div className={styles.solutionMark}><Image src="/favicon.svg" alt="" width={44} height={44} /></div><h3>One upload.<br />Zero chasing.</h3><p>Everyone gets a simple way to find the pictures they&apos;re actually in.</p></article>
      </div>
    </section>
    <section className={styles.stepsSection} id="how-it-works" aria-labelledby="steps-title">
      <div><p className={styles.label}>FIVE SIMPLE STEPS</p><h2 id="steps-title">From camera roll<br />to <em>everyone&apos;s roll.</em></h2><p className={styles.intro}>Built for the person who ends up with all the photos and all the requests.</p><Link className={styles.darkButton} href="/register">Start sharing smarter ↗</Link></div>
      <div className={styles.stepsList}>{steps.map(([number,title,body,icon]) => <article className={styles.step} key={number}><span>{number}</span><b aria-hidden="true">{icon}</b><div><h3>{title}</h3><p>{body}</p></div></article>)}</div>
    </section>
    <section className={styles.moments} id="moments" aria-labelledby="moments-title"><p className={styles.label}>SMALL GROUPS. BIG EVENTS. SAME MAGIC.</p><h2 id="moments-title">For every “send me<br /><em>my photos” moment.</em></h2><div className={styles.momentGrid}>
      <article><small>01</small><strong>🏕️</strong><h3>Trips with the gang</h3><p>Come home with memories, not a queue of photo requests.</p></article>
      <article><small>02</small><strong>💍</strong><h3>Weddings & parties</h3><p>Let every guest rediscover their favorite frames.</p></article>
      <article><small>03</small><strong>🎟️</strong><h3>Fests & events</h3><p>One place for a crowd to find their own photos.</p></article>
    </div></section>
    <section className={styles.faq} id="questions" aria-labelledby="faq-title"><div><p className={styles.label}>GOOD QUESTIONS</p><h2 id="faq-title">Before you<br /><em>say cheese.</em></h2></div><div className={styles.faqList}>{faqs.map(([question,answer]) => <details key={question}><summary>{question}<span>+</span></summary><p>{answer}</p></details>)}</div></section>
    <section className={styles.finalCta}><p>YOUR CAMERA ROLL WILL THANK YOU</p><h2>Let the memories travel.<br /><em>Not the requests.</em></h2><Link className={styles.finalButton} href="/register">Create your event ↗</Link></section>
    <footer className={styles.footer}><BrandLogo href="/" /><p>More moments. Less “photo bhej na.”</p><div><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link><Link href="/login">Log in</Link></div></footer>
  </main>;
}

