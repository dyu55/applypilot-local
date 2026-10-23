# Job sources

Enable sources in Settings. Every enabled source is collected once per user-initiated run.
The UI reports imported counts, duplicates, and source issues separately. There is no
automatic retry schedule or requirement to fill an arbitrary daily quota.

## Greenhouse

Enter an employer's public board token, such as the identifier in its Greenhouse careers
URL. The adapter reads the public jobs endpoint with `content=true`, up to 250 postings.
The board token is used as the company label when the API does not supply a display name.
An update timestamp is not treated as the original posting date.

Reference: https://docs.greenhouse.io/job-board.html

## Lever

Enter the employer's board name. Set the region to `eu` for the EU API, or leave `us` for
the global API. The adapter reads at most 250 postings and includes responsibility lists.

Reference: https://github.com/lever/postings-api

## Remote OK

The optional query filters the feed's title and tags. The adapter reads at most 100 matching
postings. Remote work may still require a particular location or authorization. Listings
link back to Remote OK and identify it as the source; do not remove that attribution.

Reference and current API terms: https://remoteok.com/api

## Adzuna search

Create your own Adzuna developer account and configure its key and app ID as environment
variables before starting the server. Enter a supported two-letter country code and query.
The adapter reads one result page, up to 50 jobs. It does not reuse predicted salary figures
as employer-disclosed salary. Search results retain unknown availability until you verify them.
Quotas and source availability depend on your provider account and region.

Reference: https://developer.adzuna.com/overview

## CSV and URL imports

CSV input is validated before import. The importer does not treat an empty field as a
confirmed false answer. URLs must use HTTP(S) without embedded credentials. Direct page
import requires structured `JobPosting` data so a generic company page is not mistaken
for a vacancy. Unreadable pages can be entered manually.

Unknown dates and salaries are not inferred from unrelated numbers. Source failures do
not turn an existing posting into an expired job. Reimporting the same posting retains its
original user status and history; it is not a general refresh operation in v0.1.

Public source requests use standard HTTP(S) ports, validate redirects, reject private-network
addresses, enforce a size limit, and make only limited retries for network errors. The
application does not bypass CAPTCHA, bot checks, logins, or paid access.
