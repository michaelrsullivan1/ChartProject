import { type ReactNode } from "react";

type TweetPreviewAuthor = {
  username: string;
  display_name: string | null;
  profile_image_url?: string | null;
};

type TweetPreviewTweet = {
  platform_tweet_id: string;
  url?: string | null;
  text: string;
  created_at_platform: string;
  reply_count?: number | null;
  repost_count?: number | null;
  like_count?: number | null;
  bookmark_count?: number | null;
};

type TweetPreviewStat = {
  label: string;
  value: number | string | null;
  icon?: "reply" | "repost" | "like" | "bookmark";
  tone?: "default" | "accent";
};

type TweetPreviewCardProps = {
  author: TweetPreviewAuthor;
  tweet: TweetPreviewTweet;
  className?: string;
  summary?: ReactNode;
  footer?: ReactNode;
  extraStats?: TweetPreviewStat[];
};

const integerFormatter = new Intl.NumberFormat("en-US");
const compactCountFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const tweetTimestampFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

export function TweetPreviewCard({
  author,
  tweet,
  className,
  summary,
  footer,
  extraStats = [],
}: TweetPreviewCardProps) {
  const href = resolveTweetUrl(author.username, tweet.platform_tweet_id, tweet.url ?? null);
  const stats = buildDefaultStats(tweet).concat(extraStats);
  const cardClassName = ["tweet-preview-card", className].filter(Boolean).join(" ");

  const card = (
    <div className={cardClassName}>
      <div className="tweet-preview-header">
        <div className="tweet-preview-identity">
          {author.profile_image_url ? (
            <img
              alt={author.display_name ?? author.username}
              className="tweet-preview-avatar"
              src={author.profile_image_url}
            />
          ) : (
            <div className="tweet-preview-avatar tweet-preview-avatar-fallback" aria-hidden="true">
              {buildAvatarInitials(author)}
            </div>
          )}
          <div className="tweet-preview-author-block">
            <p className="tweet-preview-name">{author.display_name ?? author.username}</p>
            <p className="tweet-preview-handle">@{author.username}</p>
          </div>
        </div>
      </div>

      {summary ? <div className="tweet-preview-summary">{summary}</div> : null}

      <p className="top-tweet-text">{tweet.text}</p>
      <p className="tweet-preview-timestamp">
        {formatTweetTimestamp(tweet.created_at_platform)}
      </p>

      {stats.length > 0 ? (
        <div className="tweet-preview-actions" aria-label="Post engagement">
          {stats.map((stat) => (
            <TweetActionStat
              key={`${stat.label}-${stat.icon ?? "plain"}`}
              icon={stat.icon}
              label={stat.label}
              tone={stat.tone ?? "default"}
              value={stat.value}
            />
          ))}
        </div>
      ) : null}

      {footer ? <div className="tweet-preview-footer">{footer}</div> : null}
    </div>
  );

  if (!href) {
    return card;
  }

  return (
    <a className="tweet-preview-link" href={href} rel="noreferrer" target="_blank">
      {card}
    </a>
  );
}

function TweetActionStat({
  icon,
  label,
  tone,
  value,
}: {
  icon?: "reply" | "repost" | "like" | "bookmark";
  label: string;
  tone: "default" | "accent";
  value: number | string | null;
}) {
  return (
    <span
      aria-label={`${label}: ${formatAriaValue(value)}`}
      className={`tweet-action-stat${icon ? ` tweet-action-stat-${icon}` : ""}${tone === "accent" ? " is-accent" : ""}`}
      title={label}
    >
      {icon ? (
        <span className="tweet-action-icon" aria-hidden="true">
          {renderActionIcon(icon)}
        </span>
      ) : null}
      <span>{formatDisplayValue(value)}</span>
    </span>
  );
}

function buildDefaultStats(tweet: TweetPreviewTweet): TweetPreviewStat[] {
  const stats: TweetPreviewStat[] = [];

  if ("reply_count" in tweet) {
    stats.push({ icon: "reply", label: "Replies", value: tweet.reply_count ?? 0 });
  }
  if ("repost_count" in tweet) {
    stats.push({ icon: "repost", label: "Reposts", value: tweet.repost_count ?? 0 });
  }
  if ("like_count" in tweet) {
    stats.push({ icon: "like", label: "Likes", value: tweet.like_count ?? 0, tone: "accent" });
  }
  if ("bookmark_count" in tweet) {
    stats.push({ icon: "bookmark", label: "Bookmarks", value: tweet.bookmark_count ?? 0 });
  }

  return stats;
}

function formatDisplayValue(value: number | string | null): string {
  if (typeof value === "string") {
    return value;
  }

  return formatCompactCount(value ?? 0);
}

function formatAriaValue(value: number | string | null): string {
  if (typeof value === "string") {
    return value;
  }

  return integerFormatter.format(value ?? 0);
}

function formatTweetTimestamp(value: string): string {
  const parts = tweetTimestampFormatter.formatToParts(new Date(value));
  const hour = parts.find((part) => part.type === "hour")?.value ?? "";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "";
  const dayPeriod = parts.find((part) => part.type === "dayPeriod")?.value?.toUpperCase() ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const year = parts.find((part) => part.type === "year")?.value ?? "";

  return `${hour}:${minute} ${dayPeriod} · ${month} ${day}, ${year}`;
}

function formatCompactCount(value: number): string {
  if (value < 10_000) {
    return integerFormatter.format(value);
  }

  return compactCountFormatter.format(value).toUpperCase();
}

function buildAvatarInitials(author: TweetPreviewAuthor): string {
  const source = author.display_name ?? author.username;
  const parts = source
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return "?";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function resolveTweetUrl(
  username: string,
  platformTweetId: string,
  explicitUrl: string | null,
): string | null {
  if (explicitUrl) {
    return explicitUrl;
  }

  if (!username || !platformTweetId) {
    return null;
  }

  return `https://x.com/${username}/status/${platformTweetId}`;
}

function renderActionIcon(icon: "reply" | "repost" | "like" | "bookmark") {
  switch (icon) {
    case "reply":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M21 12c0 4.4-4 8-9 8-1 0-2-.1-2.9-.4L4 21l1.5-4A7.5 7.5 0 0 1 3 12c0-4.4 4-8 9-8s9 3.6 9 8Z" />
        </svg>
      );
    case "repost":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M17 4 21 8l-4 4" />
          <path d="M3 11V9a1 1 0 0 1 1-1h17" />
          <path d="M7 20 3 16l4-4" />
          <path d="M21 13v2a1 1 0 0 1-1 1H3" />
        </svg>
      );
    case "like":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M12 20.3s-7-4.4-9.3-8.3C.9 8.9 2.2 5.5 5.7 4.7c2-.4 4 .4 5.3 2 1.3-1.6 3.3-2.4 5.3-2 3.5.8 4.8 4.2 3 7.3-2.3 3.9-9.3 8.3-9.3 8.3Z" />
        </svg>
      );
    case "bookmark":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4-7 4V4.5a1 1 0 0 1 1-1Z" />
        </svg>
      );
  }
}
