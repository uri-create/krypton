# Running Krypton for lots of people at once

## Where things stand

Krypton runs on **Streamlit Community Cloud's free plan**: one small server (about 1 GB of memory and a
share of one processor). Krypton has been made as light as possible for it:

- Only the tab a visitor is looking at is built (it used to build all 9 tabs for every visitor).
- All live data is downloaded **once** and shared by every visitor; nobody waits for downloads after the
  first visit.
- Charts are made in a lighter way, so they're quicker to send to the browser.

**Measured:** opening Krypton now costs the server about **0.17 seconds** of work per visitor, down from
**1.53 seconds** (about 9 times less). On the free server that's roughly a few hundred people actively using
it at the same time. **Thousands at the same time is more than one free server can do**, however light
the app is: for that, Krypton needs a host that runs several copies of it side by side.

## Moving to a host that grows with visitors

Krypton is ready for this: the `Dockerfile` in this folder is the recipe. Any of these hosts can run it, and
they can add more copies of Krypton automatically when more people arrive. Every copy uses the same Neon
database, and the 9-day login keeps people logged in whichever copy they land on.

| Host | Grows automatically? | Rough cost | Notes |
|---|---|---|---|
| **Google Cloud Run** | Yes (0 to 100+ copies) | Pay per use: about $0 when quiet, roughly $50-300/month for thousands of people at once | Best fit. Turn on "session affinity" and allow at least 2 GB memory per copy. |
| **Render** | Yes, on paid plans | From about $25/month per copy | Simple dashboard. |
| **Railway** | Manual (choose the number of copies) | About $5-20/month per copy | Very simple. |
| Streamlit Community Cloud | No | Free | Today's setup: fine for hundreds, not thousands. |

All of these need an account, and paid hosts need a card, so **a parent has to set it up** (like Stripe).

### Steps (Google Cloud Run, about 30 minutes)

1. A parent creates a Google Cloud account and a project, and installs the `gcloud` tool.
2. From this folder, run:

   ```bash
   gcloud run deploy krypton --source . --region us-east1 --allow-unauthenticated --memory 2Gi --cpu 2 --concurrency 80 --min-instances 1 --max-instances 50 --session-affinity
   ```

3. In the Cloud Run page for `krypton`, add the secrets as **environment variables**: `DATABASE_URL`,
   `ANTHROPIC_API_KEY`, and later `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID` and `APP_URL` (the new web address).
4. **Database:** in Neon, copy the **pooled** connection string (its address contains `-pooler`) and use
   that as `DATABASE_URL`. It lets many copies of Krypton share the database safely. Neon's free plan has
   limits on how much the database can work at once; for thousands of people, a paid Neon plan (from about
   $19/month) is safer.

## Other limits to know about

- **Data sources:** each copy of Krypton downloads the live data on its own. Free sources (especially Yahoo
  Finance) may slow down or refuse if too many copies ask too often; paid data plans fix that (see
  DATA_LICENCES.md).
- **AI costs** don't grow with visitors: AI is Krypton Pro only, with a $5/month limit per subscriber.
