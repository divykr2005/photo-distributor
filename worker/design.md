I checked the library and framework specifics before answering, since two of your open questions depend on current behavior. Here’s the file.
# design.md — Impeccable UI Reboot (Event Photo Matcher) Status: design authority document. Supersedes ad-hoc styling decisions. Scope: aesthetic system, motion policy, component contracts, per-route state map. Routes are frozen. Nothing in this document adds or removes a route.
0. Verdict on the proposal
Proceed with Zinc / Electric Blue / sans + mono. Four amendments, each of which I’d argue is a taste correction rather than a preference:
Glass is chrome, not content. Frosted surfaces over photographic content turn into mud — backdrop-blur sampling a busy image grid produces a grey smear with no edge definition, and it costs compositor work on every scroll frame. Restrict bg-white/5 backdrop-blur-xl to floating chrome: sidebar, sticky toolbars, modal scrims, lightbox controls, toasts. Content cards get an opaque zinc-900 fill. This actually reads as more premium, because the glass then means something.
One accent is not enough for this app. Match review is a three-state decision surface (pending / approved / rejected), and clustering has a selected state. Indigo alone forces you to encode semantics in text. Keep indigo as the single interactive accent — it owns “you can click this” and “this is active” — and add a semantic triad used only as 1px borders, dots, and text, never as button fills. That preserves the restraint you’re after while making the review screen legible at a glance.
Density 4 is right for the shell and wrong for the grid. An “art gallery feel” in a photo grid does not mean generous whitespace between photos; it means the opposite. Whitespace belongs around the grid. Inside it, gutters go to 4–8px, thumbnails lose their cards, and the images carry the composition. Padded cards around every photo is stock-dashboard language.
Optimistic-vanish on Approve/Reject is a real product risk here. This is face matching. A wrong approval delivers a stranger’s photos to a guest, and an instant fade-out with a “success” toast gives the organizer no recovery path. Replace “disappears immediately” with a 5-second collapse-and-undo: the card shrinks to a 32px mono strip reading APPROVED · UNDO, then removes itself. Same perceived speed, reversible.
1. Tokens
If the project is on Tailwind v4, do not create or keep tailwind.config.ts — v4 moved to CSS-first configuration, where @theme does essentially everything the JS config did, and theme variables in a namespace like --color-* are what cause the corresponding utilities to exist at all ([Tailwind theme docs](https://tailwindcss.com/docs/theme), [v4 announcement](https://tailwindcss.com/blog/tailwindcss-v4)).
/* app/globals.css */ @import "tailwindcss"; @theme { /* ---- Foundation. Zinc, unmodified. oklch values are Tailwind v4 defaults. ---- */ --color-void: oklch(14.1% 0.005 285.823); /* zinc-950 — page */ --color-surface: oklch(21% 0.006 285.885); /* zinc-900 — cards, inputs */ /* ---- Interactive accent. Owns clickability + active state. Nothing else. ---- */ --color-accent: oklch(51.1% 0.262 276.966); /* indigo-600 — fills */ --color-accent-hover:oklch(58.5% 0.233 277.117); /* indigo-500 */ --color-accent-text: oklch(67.3% 0.182 276.935); /* indigo-400 — on dark text/icons */ /* ---- Semantic. Borders, dots, text only. Never a button fill. ---- */ --color-ok: oklch(69.6% 0.17 162.48); /* emerald-500 — approved, matched */ --color-warn: oklch(76.9% 0.188 70.08); /* amber-500 — pending, low confidence */ --color-bad: oklch(64.5% 0.246 16.439); /* rose-500 — rejected, destructive */ /* ---- Type ---- */ --font-sans: "Geist Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; --font-mono: "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; /* ---- Motion. Asymmetric by policy: exits fast, entrances gentler. ---- */ --ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1); --duration-exit: 150ms; --duration-enter: 240ms; --duration-morph: 400ms; }
If you load Geist through a font loader that emits a CSS variable, wire it with @theme inline { --font-sans: var(--font-geist-sans); }. The inline keyword matters — without it the utility references the theme variable rather than its value, and resolution happens where --font-sans was defined, so a font variable declared deeper in the tree silently falls back to sans-serif.
Geist is a good fit and a real pairing: Geist Sans, Geist Mono and Geist Pixel are one family from Vercel, built with Basement Studio and Andrés Briganti, and [Geist Mono](https://fonts.google.com/specimen/Geist+Mono) is on Google Fonts. One caveat on taste: Geist is explicitly a developer/designer typeface built around simplicity and speed, which is exactly right for the organizer dashboard and slightly cold for a wedding guest. Use it everywhere for consistency, but on guest routes push size and line-height up (text-base/leading-relaxed minimum) rather than switching families. Mono is for metadata only — counts, dates, access codes, confidence scores, file sizes, EXIF. Never for prose, never for button labels.
Geometry. rounded-xl cards, rounded-lg inputs, rounded-[3px] thumbnails in dense grids, rounded-full only for avatars and status dots. Borders do the work of shadows: border-white/10 at rest, border-white/20 on hover, plus the inset highlight shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] on glass chrome only. No drop shadows on a dark canvas; they read as dirt.
Guest-route contrast floor. Guests open /register/[eventId] and /g/[accessCode] outdoors, on phones, at maximum brightness. Dark mode lock stays, but on those two routes body text is zinc-200 not zinc-400, borders are white/15, and the primary CTA is a solid indigo fill at 48px minimum height. No text-white/50 anywhere a guest has to read.
2. Motion policy — answering the open question
Install motion and import from motion/react, but ship it lazily, and do not use it for the majority of the interactions in your spec. The numbers, from [Motion’s own bundle guidance](https://motion.dev/docs/react-reduce-bundle-size): the declarative motion component cannot be tree-shaken below 34kb because of its props-driven API. Swapping to the m component under <LazyMotion> brings initial render to ~4.6kb, with feature packages adding +15kb (domAnimation: animations, variants, exit animations, tap/hover/focus) or +25kb (domMax: adds drag and layout animations). Separately, useAnimate comes in a 2.3kb mini build (WAAPI-only) and a 17kb hybrid.
So the policy is a three-tier ladder, cheapest tier first:
Tier 1 — CSS, no JS. Everything in your spec marked hover, active, focus, disabled, spinner, skeleton shimmer, and the “Copied!” swap. transition-colors, active:scale-[0.98], active:-translate-y-px, animate-spin, animate-pulse, focus-visible:ring-2 focus-visible:ring-indigo-500. This covers roughly all of section 2 of your plan.
Tier 2 — React <ViewTransition>, no library. This is the one I’d most strongly push you toward, because the canonical Next.js example for it is literally a photo gallery. It works in the App Router with no configuration (the App Router runs React canary, so you don’t install react@canary yourself), and it degrades to instant swaps where the browser doesn’t support it. From the [Next.js view transitions guide](https://nextjs.org/docs/app/guides/view-transitions):
Thumbnail → lightbox/hero morph. Wrap grid thumb and detail hero in <ViewTransition name={photoId}>. React pairs them and animates size/position with zero CSS. Add a blur keyframe mid-flight to hide interpolation artifacts. The morph only plays when the destination renders in the same commit, so prefetch the detail route — otherwise a Suspense fallback breaks the pair and you get a plain enter animation.
Skeleton → gallery handoff. Wrap the Suspense fallback with an exit and the content with an enter, using the asymmetric timings above (150ms exit, enter fade delayed until the exit finishes, 400ms slide over a 60px offset). This is a better answer than your “skeleton loaders for galleries” line, because the skeleton yields to the photos instead of popping out of existence.
Directional route slides. transitionTypes={['nav-forward']} on <Link>, nav-back on breadcrumb links, mapped in enter/exit objects with default: "none".
Gotchas that will bite you: default="none" is required on named transitions or every named element animates on every unrelated transition — but if you set default="none" on a pair and drop the explicit share, the morph silently stops. Pin the dashboard sidebar/header with a viewTransitionName and suppress its animation (display: none on the old snapshot, high z-index) or the whole viewport appears to slide. And add ::view-transition { pointer-events: none } or clicks during a transition are swallowed by the overlay.
Tier 3 — m + LazyMotion. Reserve for the three places CSS genuinely can’t reach: AnimatePresence exit on review-card removal (Tier-1 CSS can’t animate an unmounting node), the cluster merge layout animation (needs domMax), and drag-reorder if it ever ships. Load domAnimation synchronously in the dashboard layout, dynamic-import domMax only on the clusters route, and set <LazyMotion strict> so a stray motion.div import can’t silently re-add the 34kb.
Reduced motion is non-negotiable. Directional slides are the most common motion-sensitivity trigger. Zero out animation durations under prefers-reduced-motion; morphs and crossfades can survive, positional translation cannot.
3. Button contract
One component, [cva](https://cva.style/) for variants, with the loading state as a variant of the same button rather than a separate spinner element — that’s what prevents the width jump that makes loading states feel cheap.
const button = cva( ["relative inline-flex items-center justify-center gap-2", "font-medium select-none whitespace-nowrap", "rounded-lg border transition-[colors,transform] duration-150", "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950", "active:scale-[0.98] active:-translate-y-px", "disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100 disabled:active:translate-y-0"], { variants: { variant: { primary: "bg-indigo-600 border-indigo-500/40 text-white hover:bg-indigo-500", secondary: "bg-white/5 border-white/10 text-zinc-100 hover:bg-white/10 hover:border-white/20", ghost: "bg-transparent border-transparent text-zinc-400 hover:bg-white/5 hover:text-zinc-100", outline: "bg-transparent border-white/15 text-zinc-200 hover:border-white/30 hover:bg-white/5", destructive: "bg-transparent border-rose-500/30 text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/50", }, size: { sm: "h-8 px-3 text-xs", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" }, state: { idle: null, loading: "cursor-wait [&>[data-label]]:opacity-0", success: "border-emerald-500/40 text-emerald-400", }, }, compoundVariants: [ // destructive at rest is quiet; only the armed confirm state goes loud. { variant: "destructive", state: "loading", class: "bg-rose-500/10" }, ], defaultVariants: { variant: "secondary", size: "md", state: "idle" }, } );
Rules that go with it. The label lives in a <span data-label> and the spinner is absolutely centered on top, so the button never changes width mid-flight — no measuring, no layout shift. Loading sets disabled and aria-busy="true". The success state is time-boxed to 2000ms then returns to idle, and its text change is announced via a polite aria-live region (a silent icon swap is invisible to screen readers). Destructive actions are two-step but never double-click — double-click is undiscoverable and misfires. Icon-only buttons require aria-label and a tooltip. Progress-bearing buttons render the fill as an absolutely-positioned inset-y-0 left-0 bg-indigo-500/25 layer behind the label, with the percentage in mono to the right of it.
4. Layout shells
Dashboard. Fixed 240px left rail, bg-white/[0.03] backdrop-blur-xl border-r border-white/5, containing the event switcher at top (mono event name + guest count), nav items at 36px height with the active item marked by a 2px indigo left bar plus text-zinc-100 — not a filled pill, which is the tell of a bootstrapped admin panel. Main column max-w-[1400px] with px-8 py-6. The asymmetric split at Variance 6 belongs on the event overview (a 2fr/1fr grid: photo activity left, registration link and stats card right) and on the review screen (candidate photo left at 60%, guest reference face and confidence metadata right).
Auth. Two columns at lg:. Left is the form, max-w-sm centered in its half. Right is a single full-bleed event photograph at opacity-40 with a bg-gradient-to-r from-zinc-950 wash — this is where the product’s actual value lives, so show it. Collapses to form-only on mobile with no image download.
Public/guest. Single centered column, max-w-md, no sidebar, no dashboard chrome. A guest should never see the organizer’s information architecture.
Route progress. A 2px indigo indeterminate bar pinned to the top of the viewport, driven by React transition/pending state, rendered above the view-transition layer.
5. Route → interaction state map
Paths unchanged. S = static, D = dynamic.
Route
Element
Kind
Specified behavior
app/page.tsx
Login
S ghost
hover bg-white/5 only
Register
S outline
—
Get Started
S primary
magnetic hover: translate ≤4px toward cursor, spring, disabled under reduced-motion
app/privacy
Return to Home
S link
underline on hover, text-indigo-400
(auth)/login, (auth)/register
Sign In / Create Account
D primary
label→spinner in place, width locked, aria-busy, form inputs disabled
Google / GitHub
S outline
brand mark left, label centered
register/[eventId]
Upload Selfie
D trigger
dashed border-white/15 drop zone → on select, 96px rounded-full preview + face-detection check (ok ring) or warn retake prompt
Complete Registration
D primary
determinate for upload %, then indeterminate “Analyzing” for vectorization — two honest phases, one bar
g/[accessCode]
Download All Photos
D primary
three named states: QUEUED → ZIPPING n/N (mono, from server count) → READY. Never a fabricated percentage
Request Data Deletion
D destructive
modal, typed confirmation of the event name, plain-language statement of what is erased (face vector, photos, access code), then PURGING
(dashboard)/dashboard
Create New Event
S primary
—
View All Events
S secondary
—
(dashboard)/events
New Event
S primary
top-right of page header
View Event
S ghost
whole card is the hit target; button is visual affordance only
events/new
Create Event
D primary
in-place spinner, inputs locked
events/[eventId]
Upload Photos
S primary link
—
Review Matches
S secondary link
mono pending count as a trailing badge
Copy Registration Link
D utility
icon→check, label→Copied!, 2000ms, aria-live="polite"
events/[eventId]/upload
Select Files
D input
drop zone: border-white/15 → border-indigo-500/60 bg-indigo-500/5 on drag-over
Upload X Photos
D primary
determinate fill behind label, mono n/N + throughput; per-thumbnail ring progress in the queue below
events/[eventId]/photos
Refresh
D icon
animate-spin while fetching, min 400ms so it’s perceptible
Delete Photo
D destructive icon
appears on hover, top-right of thumbnail, confirm required, removal animates out via AnimatePresence
events/[eventId]/clusters
Name Cluster
D outline
morphs to inline input + Save, autofocus, Enter commits, Escape reverts
Merge Clusters
D action
disabled until ≥2 selected; label shows the count; layout animation on merge
events/[eventId]/review
Approve / Reject
D per-match
collapse to a 32px mono APPROVED · UNDO strip for 5s, then remove. Keyboard: A/R/U
Approve All
D primary
modal stating the exact count first, then spinner; disabled below a confidence floor
guests, guests/[guestId]
View Profile
S link
—
Delete Guest
D destructive
same typed-confirmation pattern as guest-side deletion
6. Photo grid specifics
grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6, gap-1, no card wrapper. Every cell declares its aspect ratio before the image loads so the grid never reflows — pair that with a blur-up placeholder if your image component supports one, and drop the generic pulsing-rectangle skeleton entirely; a shimmering grey box that then jumps is worse than a correctly-sized blur that resolves. Hover raises the cell to opacity-100 from opacity-[0.92], reveals the delete affordance, and shows a bottom gradient strip carrying mono metadata (match count, timestamp). Selection is a 2px indigo inset ring plus a filled check in the top-left, not a scale change — scaling breaks the grid rhythm. Lightbox is a full-viewport bg-zinc-950/95 backdrop-blur-2xl scrim with the image morphing in via <ViewTransition> and all controls in glass chrome at the edges.
7. Trust is a design surface
For a product that stores biometric data, the privacy UI is the premium signal — restraint elsewhere earns nothing if this part is vague. Concretely: the guest registration screen states what is stored and for how long in mono, above the CTA, not behind a link. The guest portal carries a persistent retention line (FACE DATA · DELETED 30D AFTER EVENT) and a permanently visible deletion entry point. Confidence scores are shown as mono numerals with a semantic dot, never as a bare progress bar that implies false precision. No AI-branded gradients, sparkle icons, or “magic” copy anywhere — the matching is a utility, and treating it as one is what makes it trustworthy.
8. Build order
Tokens and globals.css first, then Button.tsx with the full variant matrix and a visual state page for review, then the two layout shells, then form primitives (bg-zinc-900, border-white/10, focus:ring-indigo-500, labels above, error text in text-rose-400 with aria-describedby), then the photo grid and lightbox with view transitions, then the review and cluster screens, and only then Tier-3 motion. Ship the accessibility pass — focus order, aria-live regions, reduced-motion, 48px guest touch targets — as part of each step rather than as a phase, because retrofitting it into a cva matrix afterwards means rewriting the matrix.
Sources consulted: [Tailwind v4 CSS-first config](https://tailwindcss.com/blog/tailwindcss-v4) · [Tailwind theme variables](https://tailwindcss.com/docs/theme) · [Motion bundle size](https://motion.dev/docs/react-reduce-bundle-size) · [LazyMotion](https://motion.dev/docs/react-lazy-motion) · [Next.js view transitions](https://nextjs.org/docs/app/guides/view-transitions) · [cva variants](https://cva.style/getting-started/variants/) · [Geist](https://github.com/vercel/geist-font)
Two things I flagged but left as your call rather than deciding for you: whether the semantic triad is acceptable to you at all given your “single accent color” rule (I think the review screen needs it, but it is a genuine departure from your spec), and whether to keep dark mode locked on guest routes or allow a light variant there — I kept it locked and raised contrast instead, since brand consistency across the organizer→guest handoff is probably worth more than the daylight legibility you’d win.
