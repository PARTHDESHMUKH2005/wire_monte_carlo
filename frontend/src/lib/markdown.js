"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function SafeMarkdown({ content, className = "vera-markdown" }) {
  if (!content) return null;
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
