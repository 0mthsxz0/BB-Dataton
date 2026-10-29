/** Session-only aggregate counters. No query, identifiers or network transmission. */
const counts={searches:0,empty:0,clarifications:0,answers:0,selections:0,errors:0,offline:0};
export function recordActivityMetric(name){if(Object.hasOwn(counts,name))counts[name]++;}
export function activityMetrics(){return {...counts,engine:'local-rules-tfidf-v3'};}
