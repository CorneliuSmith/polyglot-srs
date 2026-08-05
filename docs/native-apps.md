# iOS and Android apps

The native apps are the existing web app in a Capacitor shell. There is no
second codebase: `frontend/` builds once and both platforms load the same
bundle.

## Why Capacitor and not React Native

The app was already mobile-first — a bottom tab bar, safe-area insets, an
on-screen keyboard for non-Latin scripts, a service worker, six UI locales
and 22 letter guides. A React Native port would reimplement every screen to
arrive at the same screens. Capacitor keeps one codebase and one test
suite; the trade is that anything needing a genuinely native control (a
system share sheet, widgets) has to come through a plugin.

## Layout

```
frontend/
  capacitor.config.ts   identity, splash, keyboard behaviour
  src/lib/native.ts     the shell wiring — a no-op in a browser
  android/              generated Android project (committed)
  ios/                  generated Xcode project (committed)
```

Both platform directories are committed, which is the standard Capacitor
layout: they hold real configuration (permissions, signing, icons) that
would otherwise be recreated from scratch on every machine. Build outputs
and the copied web assets are gitignored — `android/app/build`,
`ios/App/Pods`, `android/app/src/main/assets/public`.

## Assets are bundled, not remote

`capacitor.config.ts` sets `webDir: 'dist'` and deliberately does **not**
set `server.url`. Pointing the shell at the live site is faster to set up
and gets an app rejected under App Store guideline 4.2 for being a website
in a wrapper, and it fails completely offline. The bundle ships inside the
binary and talks to the API over HTTPS like any other client.

The consequence: **shipping a web change to the apps means shipping a new
build.** The web app updates on deploy; the apps update on review. Plan
anything time-sensitive (a pricing change, a content deadline) around the
slower of the two.

## Working on them

```bash
cd frontend
npm run native:sync        # build the web app and push it into both shells
npm run native:android     # ...then open Android Studio
npm run native:ios         # ...then open Xcode  (macOS only)
npm run native:live        # live reload on a handset over the LAN
```

`cap sync` is not the same as copying files: it also re-links native
plugins, so run it after adding or upgrading any `@capacitor/*` package.

## What still needs doing before a store submission

This is a working baseline, not a submitted app. None of the following can
be done from CI — each needs the platform toolchain and a developer
account:

1. **Icons and splash screens.** The PWA icons in `frontend/public` are the
   source material; run `@capacitor/assets` to generate the full native set
   into both projects.
2. **Signing.** An Apple Developer account with a distribution certificate
   and provisioning profile; a Play upload key and keystore. Never commit
   the keystore or the `.p12`.
3. **Permissions and usage strings.** The app records audio for the tutor,
   so `NSMicrophoneUsageDescription` needs real copy in `Info.plist` and
   `RECORD_AUDIO` needs declaring in the Android manifest. Apple rejects a
   missing or boilerplate usage string.
4. **Deep links.** `src/lib/native.ts` already routes `appUrlOpen`; the
   domain association files (`apple-app-site-association`,
   `assetlinks.json`) still need serving from the API host.
5. **Store listings.** Screenshots per device class, description,
   privacy-policy URL, and the data-collection disclosure — both stores
   require an accurate account of what the tutor sends to the model
   provider.
6. **Testing on real devices.** RTL locales (Arabic, Hebrew, Persian) and
   the on-screen keyboards are the highest-risk areas: they behave
   differently in a WebView than in mobile Safari or Chrome, and no
   emulator substitutes for a physical handset here.

## What was verified here, and what was not

Verified: the web build, the TypeScript across the whole project graph, and
the full frontend test suite, with the Capacitor wiring in place. Both
platform projects generate cleanly and carry the right bundle identifier
(`com.polyglotsrs.app`) and app name.

**Not verified: neither native project has been compiled.** Building the
iOS app needs Xcode on macOS, and the Android app needs the Android SDK;
neither exists in CI. The first `./gradlew assembleDebug` and the first
Xcode build may well surface something — treat them as the next step, not
as a regression.
