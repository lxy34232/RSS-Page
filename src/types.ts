export interface FeedEntry {
  title: string;
  link: string;
  pubDate?: string;
  description?: string;
}

export interface Recommendation {
  title: string;
  url: string;
  description?: string;
}

export interface Source {
  name: string;
  url: string;
  entries: FeedEntry[];
}

export interface Group {
  groupName: string;
  sources: Source[];
}

export interface FeedData {
  lastUpdated: string;
  daysFilter: number;
  groups: Group[];
}

export interface RecommendationsData {
  recommendations: Record<string, Recommendation[]>;
}
