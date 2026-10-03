# Setup & Deploy

> This repo is wired to the maintainer's Firebase project (`shelf-date-check`). To run your **own** copy, point `public/firebase-config.js` and the owner email in `firestore.rules` at your own Firebase project before deploying. The steps below otherwise apply.


Your own copy of the shop's date check app, with a login for every staff member and a morning and evening check round. It runs on Google Firebase on the free plan, at a normal web address staff can add to their home screen. No Claude account needed.

What's in this folder:

- `public/` is the app itself (index.html, app.js, icons)
- `public/firebase-config.js` has your project's details (already filled in)
- `firestore.rules` decides who can read and change the data (already set to your owner email)
- `firebase.json` and `.firebaserc` tell Firebase how to deploy it

Before deploying, point the app at your own Firebase project:

1. Copy `public/firebase-config.example.js` to `public/firebase-config.js` and fill in your web app config and your `OWNER_EMAIL`.
2. In `firestore.rules`, set the email in `isOwner()` to that same owner email.
3. In `firebase.json`, set `hosting.site` to your Hosting site name (and `.firebaserc` to your project id).

Then follow the console steps below. About 15 minutes.

## 1. Create the owner login (if you haven't already)

1. In the left menu go to **Build > Authentication** and click **Get started**.
2. Under **Sign-in method**, enable **Email/Password** (leave "Email link" off).
3. Go to the **Users** tab and click **Add user** with the owner email and a strong password.

The owner login is hidden from staff and is only for first-time setup and as a backup if every manager gets locked out. Staff never see that it exists. Staff logins are created from inside the app.

## 2. Create the database

1. Go to **Build > Firestore Database** and click **Create database**.
2. Choose a location in Europe, for example `europe-west1 (Belgium)` or `europe-west2 (London)`. This can't be changed later.
3. Start in **production mode**.

## 3. Owner email (already set)

The owner email is set in two places: `public/firebase-config.js` (`OWNER_EMAIL`) and `firestore.rules` (`isOwner`). Both are already filled in. If you ever change the owner account, update both and deploy again.

## 4. Put it online

You need Node.js on your computer for this part.

1. Install Node.js (the LTS version) from https://nodejs.org
2. Open a terminal in this folder and run:

```
npm install -g firebase-tools
firebase login
firebase deploy
```

`firebase login` opens a browser to sign in with the same Google account. `firebase deploy` uploads the app and the database rules. At the end it prints your address, which looks like `https://your-project-id.web.app`.

If deploy says Hosting isn't set up, run `firebase init hosting`, pick your existing project, set the public folder to `public`, answer **No** to "single-page app" and **No** to overwriting `index.html`, then run `firebase deploy` again.

## 5. First-time setup

1. Open the web address. Tap the yellow **BB** badge five times to reach the admin sign-in.
2. Sign in with the owner email (`your owner email`) and the password you set in step 1.
3. Enter the store name and create the first manager (name, username, PIN). The app signs the owner out.
4. Sign in as that manager with the username and PIN.
5. In the **Staff** tab, add the team. Each person gets a username and a 4 to 6 digit PIN.
6. In the **Staff** tab, under Date checks, add the sections you check (Dairy chiller, Bakery and so on) and set the morning and evening "due by" times.

Staff can then sign in on any phone with their own username and PIN, add the app to their home screen, and stay signed in. They can change their own PIN in the Staff tab. On a shared shop device, tap **Sign out** at the end of a shift.

The first time someone taps **Scan with camera**, the phone asks for camera permission. Tap Allow.

## Day to day

- **Updating the app:** change the files, then run `firebase deploy` again. Devices pick up the new version next time they open it.
- **Forgotten PIN:** a manager opens Staff, taps Manage on that person and sets a new PIN. The old PIN stops working straight away.
- **Someone leaves:** a manager taps Deactivate. They can no longer sign in, but their name stays on everything they logged.
- **Lost phone:** deactivate the person, then reactivate them with a new PIN.
- **Poor Wi-Fi:** the app keeps working. Anything logged offline saves on the device and syncs when the connection returns. The top bar shows "Offline" while that's happening.
- **Seeing the raw data:** Firestore Database in the console shows every item, staff member and change.

## What it costs

Nothing for one shop. The free plan allows tens of thousands of reads and writes a day, far more than a store's date checks will use. If you ever go over, Firebase stops serving until the next day rather than charging you, because the Spark plan has no card attached.

## How secure it is

- Nothing is visible until someone signs in. The sign-in screen shows no names.
- Every person has their own login. PINs are never stored in the database.
- Positions are enforced by the database rules, not just the app. Floor staff can't change positions, add people or undo removals, even with technical know-how.
- Every change is signed with the person's own identity, so nobody can log something under someone else's name.
- Items and staff can't be deleted, so the history stays honest.
- Firebase blocks repeated wrong PIN attempts. A 4 digit PIN is still short, so 6 digits is better for managers.
- Store only staff first names or names plus initial, and check with your manager that keeping this record is fine under the company's policies.

## Morning and evening checks

The Today screen opens on the current round: the morning check before opening, the evening check after 2pm. Each section is ticked off, showing who did it and when, and the evening screen also shows whether the morning round was finished. Staff get a start-of-shift summary when they sign in, and phones that support it show a count on the app icon. Alerts that arrive while the app is fully closed (push notifications) need a paid Firebase plan for the sending side, so they aren't included.
