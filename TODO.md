# TODOS 
## Various Dashboard Improvement Ideas 


------

### Snapshot and Cache More Info 

All the caching and stuff has worked way better for the aggregate users, but it might be nice to do this for some of the average users data as well... since some of them have such a gigantic dataset and it's kinda hard to navigate through all of them.

### More Timing Improvements 

When I ran this command:

`python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
--fetch-results data/exports/refresh-plans/tracked-author-refresh-plan-20260414T203424Z.fetch-results.repaired.json`

It took nearly three hours.

I've got some of this cleaned up and hopefully slighly optimized, but I feel there is more room for improvement here. I think the tagging logic ends up taking over half of the time and couple in theory clean stuff up quite a bit.

Here are some ideas from the AI:

```
1. Make normalization incremental so it processes only raw artifacts from the current refresh runs, not the user’s full raw history.

2. Make validation incremental or window-scoped so it checks only newly refreshed data instead of rebuilding expectations from all archived artifacts.

3. Make keyword extraction incremental so it only processes tweets missing keyword rows, instead of rescanning all tweets since `analysis_start`.

4. Keep sentiment and mood scoring batched across all users so models load once per run, not once per user.

5. Stop spawning as many subprocesses and call service-layer functions in-process where practical.

6. Pass refresh-specific `analysis_start` values into keyword extraction instead of always using the user’s first tweet date.

7. Batch managed-author sync and rebuild the author-registry snapshot once at the end.

8. Add per-user stage checkpoints so reruns skip stages that already completed successfully.

```


### Global/Cohort Tagging

It would be nice to see the narrative stuff on a broader basis and expand this area of the dashboard slighly to compare narratives across these cohorts

### Price Mentions by Cohort

I can sort by cohort and then look through the tweets and do price mentions and average price target is mentioned by the cohort and compared to other cohorts.

### mNAV Mentions by Cohort

I can do a similar thing here with mnav and see what numbers are getting thrown around and talked about for mnav generally. And this predictions, but which ones are talked about.


### Add User Cohort Definitions 

Explain things like: "What is an OG" and "What is a pleb"... have this show up on the aggregate page when you are selecting these groups

### Remove Tracked Authors Files

I removed so much of this tracked author stuff so I have basically no mentions of the people I have in here in the codebase. But I still have them basically always sit out in this one file right here.

`tracked_authors.py`




