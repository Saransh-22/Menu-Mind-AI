import React from 'react';

interface Props {
  content: string;
}

export const MarkdownRenderer: React.FC<Props> = ({ content }) => {
  if (!content) return null;

  // Split lines
  const lines = content.split('\n');

  return (
    <div className="space-y-1.5 text-inherit leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();

        // Empty line
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // Heading 3
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={idx} className="font-bold text-sm text-gray-900 mt-2 mb-1">
              {formatInline(trimmed.slice(4))}
            </h4>
          );
        }

        // Heading 2
        if (trimmed.startsWith('## ')) {
          return (
            <h3 key={idx} className="font-bold text-sm text-gray-900 mt-2.5 mb-1 border-b border-gray-100 pb-0.5">
              {formatInline(trimmed.slice(3))}
            </h3>
          );
        }

        // Heading 1
        if (trimmed.startsWith('# ')) {
          return (
            <h2 key={idx} className="font-bold text-base text-gray-900 mt-3 mb-1">
              {formatInline(trimmed.slice(2))}
            </h2>
          );
        }

        // Unordered list item
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          return (
            <div key={idx} className="flex items-start gap-2 ml-2">
              <span className="text-emerald-600 font-bold leading-5">•</span>
              <span className="flex-1">{formatInline(trimmed.slice(2))}</span>
            </div>
          );
        }

        // Numbered list item
        const matchNum = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (matchNum) {
          return (
            <div key={idx} className="flex items-start gap-2 ml-2">
              <span className="text-emerald-700 font-semibold font-mono text-xs">{matchNum[1]}.</span>
              <span className="flex-1">{formatInline(matchNum[2])}</span>
            </div>
          );
        }

        // Blockquote
        if (trimmed.startsWith('> ')) {
          return (
            <blockquote key={idx} className="border-l-2 border-emerald-500 pl-3 italic text-gray-600 my-1">
              {formatInline(trimmed.slice(2))}
            </blockquote>
          );
        }

        // Standard paragraph line
        return (
          <p key={idx} className="leading-relaxed">
            {formatInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
};

// Formats **bold**, *italic*, `code`, and links [text](url)
function formatInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  // Regex for **bold**, `code`, and [label](url)
  const regex = /(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))/g;
  let match: RegExpExecArray | null;
  let lastIndex = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={keyIdx++} className="font-semibold text-gray-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={keyIdx++} className="px-1 py-0.5 rounded bg-gray-100 text-emerald-800 font-mono text-[11px]">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('[') && token.includes('](')) {
      const labelEnd = token.indexOf('](');
      const label = token.slice(1, labelEnd);
      const url = token.slice(labelEnd + 2, -1);
      parts.push(
        <a
          key={keyIdx++}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-emerald-700 underline font-medium hover:text-emerald-900"
        >
          {label}
        </a>
      );
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}
