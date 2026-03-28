# ChartProject Ideas Backlog

## Product Thesis

This project should not position itself as "another sentiment dashboard."

The differentiated angle is:

- it is author-specific instead of generic market-wide sentiment
- it preserves a durable historical archive
- it can measure how one influential voice changed over time
- it can compare language, engagement, and market behavior in the same timeline
- it can surface signals that feel closer to positioning, conviction, and narrative regime shifts than simple positive/negative scoring

For an investor or Bitcoin-focused user, the value is not "this tweet was bullish."

The value is more like:

- did this account get more aggressive before or after major moves?
- when does tone diverge from price?
- when does engagement confirm a narrative shift?
- what kinds of tweets tend to precede strong BTC or MSTR follow-through?
- when is the account unusually loud, unusually quiet, unusually confident, or unusually effective?

That framing is stronger because it points toward action, not just curiosity.

## Best Investor-Facing Angles

### 1. Lead/Lag Signal Detection

The most interesting product question is whether changes in an author's tone, activity, or engagement tend to lead price action or simply react to it.

Ideas:

- show forward BTC returns after extreme sentiment weeks
- show forward BTC returns after top-decile tweet activity weeks
- show forward BTC returns after top-decile engagement weeks
- compare 1-day, 3-day, 7-day, and 30-day outcomes
- show whether "high conviction + high engagement" has historically been more predictive than sentiment alone

Why it matters:

- this moves the app from descriptive to testable
- investors can evaluate whether the signal has any historical edge

### 2. Divergence Detection

Some of the most interesting moments will be when the author's behavior and the market disagree.

Examples:

- very bullish sentiment while BTC is flat or down
- unusually high posting intensity during local weakness
- declining sentiment while price is still rising
- strong engagement on tweets during market exhaustion

Why it matters:

- divergence is often more actionable than raw sentiment
- it creates specific setups to watch instead of passive charts

### 3. Conviction Index

A plain sentiment score is not enough. A custom "conviction" metric would likely be more valuable.

Possible inputs:

- positive minus negative sentiment
- tweet frequency
- engagement rate
- bookmark intensity
- impression intensity
- concentration of posts within a short window
- ratio of original posts versus replies or quote tweets later

Output ideas:

- weekly conviction score
- conviction acceleration
- conviction versus BTC momentum
- conviction percentile versus history

Why it matters:

- investors care more about strength and intensity than textbook sentiment labels

### 4. Regime Shift Detection

The app can be good at spotting narrative changes that are obvious in hindsight but hard to quantify in real time.

Examples:

- transition from cautious commentary to aggressive advocacy
- phase change from educational content to overt market conviction
- shift from broad macro framing to company-specific or Bitcoin treasury framing

Potential outputs:

- timeline callouts for major tone changes
- clustering of tweet eras
- "this week looks most similar to these prior periods"

Why it matters:

- regime detection is a more interesting premium feature than another line chart

### 5. Event Study View

Investors understand event studies immediately.

Examples:

- what did BTC do after the author's top 20 most engaged tweets?
- what did BTC do after the most positive or most negative weeks?
- what did MSTR do after extreme tweet clusters?
- what happened after weeks with no tweets?

Why it matters:

- this produces simple, shareable evidence
- it creates a bridge from research tool to decision support

## Features That Could Feel Genuinely Useful

### Signal Cards

Instead of only showing charts, generate simple cards like:

- "Conviction is in the 93rd percentile versus history."
- "Sentiment is rising while BTC momentum is falling."
- "This is the strongest engagement week in 14 months."
- "Historically, weeks like this were followed by positive 7-day BTC returns 62% of the time."

This is probably the fastest route to something that feels actionable.

### Forward Return Panels

For each selected week or tweet, show:

- BTC return after 1d, 3d, 7d, 30d
- MSTR return after 1d, 3d, 7d, 30d
- percentile ranking versus all prior observations

This makes the drilldown substantially more useful.

### Sentiment vs Market Reaction Scatterplot

A useful research view would be:

- x-axis: sentiment or conviction
- y-axis: forward BTC return
- point size: engagement
- color: market regime or year

This helps answer whether the signal is real or just visually interesting.

### Narrative Term Tracking

Track specific phrases or concepts over time.

Bitcoin users will care about whether language shifts toward:

- treasury strategy
- long-term conviction
- leverage or capital markets framing
- volatility framing
- macro stress
- ETF adoption
- sovereign adoption

This becomes much more differentiated if the language is tracked historically instead of just sentiment-scored.

### "Silence Matters" View

Sometimes the absence of tweets is itself a signal.

Ideas:

- periods of unusual silence during drawdowns
- periods of unusual silence during euphoric rallies
- compare silence windows to later market moves

That is non-obvious and much more interesting than raw tweet counts alone.

### Engagement-Adjusted Sentiment

Not all tweets matter equally.

Possible variants:

- impression-weighted sentiment
- bookmark-weighted sentiment
- like-weighted sentiment
- top-decile-engagement sentiment only

This likely maps better to "market impact" than simple averages.

### Best/Worst Historical Analogues

For the current week, identify similar prior weeks based on:

- activity
- engagement
- conviction
- price momentum

Then show:

- the closest 3 analogues
- what happened next in BTC and MSTR

This is compelling for both research and demos.

## Product Directions That Increase Uniqueness

### Move From Single Metric to Signal Stack

A strong version of this app probably combines:

- sentiment
- activity
- engagement
- topic mix
- market context

One number alone will be fragile. A stack of aligned indicators is more defensible.

### Focus on Influential Accounts, Not "All of Twitter"

This project gets stronger if it leans into:

- influential Bitcoin personalities
- treasury-company executives
- macro commentators with clear market narratives

That is likely more ownable than broad crypto sentiment.

### Preserve the "Private Research Terminal" Feel

The README already points in this direction. That is a good thing.

A polished, niche research terminal can feel more premium than a generic public dashboard.

Possible positioning:

- "historical conviction analysis"
- "influence-aware market narrative tracking"
- "author-specific signal research"

## Concrete Feature Ideas By Priority

### Now

### 1. Forward Returns After Selected Week

Add forward BTC and MSTR returns to the existing week drilldown.

Why first:

- fits the current architecture
- directly answers "could this be actionable?"
- easy to understand in demos

### 2. Engagement-Weighted Sentiment Series

Add alternate sentiment modes:

- raw average
- like-weighted
- bookmark-weighted
- impression-weighted

Why first:

- you already have the data
- likely more meaningful than plain average sentiment

### 3. Conviction Score Prototype

Build a simple first-pass index from:

- standardized sentiment
- standardized tweet_count
- standardized engagement

Display it as:

- score
- percentile
- change versus prior week

Why first:

- gives you a signature metric
- can be iterated later without changing the product framing

### 4. Divergence Flags

Create simple rules such as:

- conviction up, BTC down
- conviction down, BTC up
- activity spike without price confirmation

Why first:

- cheap to implement
- easy to explain
- closer to trade setup language

### Next

### 5. Event Study Page

Build a dedicated page for:

- extreme conviction weeks
- extreme sentiment weeks
- top-engagement tweets
- no-tweet weeks

Show win rate and average forward returns.

### 6. Topic and Phrase Tracking

Start with simple keyword buckets before full topic modeling.

Possible buckets:

- Bitcoin maximalism
- treasury strategy
- AI / technology overlap
- macro fear
- adoption / institutions

### 7. Historical Analogues

For each current week, show the closest prior weeks and subsequent returns.

### 8. Market Regime Overlay

Label periods like:

- bull trend
- drawdown
- chop / range
- recovery

Then let users compare whether the author's signal behaves differently by regime.

### Later

### 9. Multi-Author Comparison

Compare:

- Saylor vs other Bitcoin voices
- executives vs analysts
- high-conviction accounts vs broader crowd

This can become a real moat if the archive grows.

### 10. Influence Propagation

Longer term, measure whether tweets are echoed by others later.

That would require more data, but it is a powerful concept:

- not just "what did he say?"
- but "did the narrative spread?"

### 11. Strategy Sandbox

Let the user define simple rules such as:

- buy when conviction > threshold and BTC 7-day momentum < 0
- fade when engagement is extreme and price is extended

Then backtest those rules roughly.

This is high value, but only after the basic signal work is credible.

## Experiments Worth Running

These are the fastest ways to see whether the project has real edge.

### Experiment 1

Does high-conviction Saylor activity precede above-average BTC forward returns?

### Experiment 2

Is engagement-weighted sentiment more predictive than raw sentiment?

### Experiment 3

Are divergence periods more predictive than aligned periods?

### Experiment 4

Do the most bookmarked tweets have different follow-through than the most liked tweets?

### Experiment 5

Are silence periods informative?

### Experiment 6

Does the signal work better for MSTR than BTC?

That last one is important because the account may map more directly to MSTR behavior than to BTC itself.

## Simple Metrics To Add

These would improve the product quickly without requiring a major model upgrade.

- engagement per tweet
- impressions per tweet
- likes per impression
- bookmarks per impression
- sentiment z-score versus trailing history
- conviction z-score versus trailing history
- 4-week and 12-week change in conviction
- forward BTC and MSTR returns from each period
- rolling correlation between conviction and price
- rolling lead/lag correlation

## Things To Be Careful About

Some ideas sound exciting but can become weak quickly if not handled carefully.

### Avoid generic "bullish/bearish"

That is too shallow and too easy to copy.

### Avoid pretending causality

The strongest framing is:

- "historically associated with"
- "tended to precede"
- "coincided with"

Not:

- "this caused BTC to move"

### Avoid overfitting too early

A lot of apparent market signal will disappear if you slice the data too aggressively.

### Avoid building a massive feature surface before a core insight exists

The highest priority is proving one or two genuinely interesting signals first.

## Suggested Build Order

1. Add forward returns to week drilldown.
2. Add engagement-weighted sentiment modes.
3. Create a simple conviction index.
4. Add divergence flagging and summary cards.
5. Build an event study page.
6. Add keyword/topic tracking.
7. Expand to multi-author comparisons.

## Working Positioning Draft

If you want a sharper way to talk about the product, something like this is stronger:

"ChartProject is a private research terminal for studying how influential Bitcoin voices change over time, how their conviction maps to engagement, and how those shifts line up with BTC and MSTR market behavior."

Or more directly:

"This is not generic social sentiment. It is author-specific conviction analysis tied to historical market outcomes."

That second sentence is probably close to the real wedge.
