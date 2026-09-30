import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { slugifyHeading, stripPhotoCredits } from "../lib/articleDocument";
import { allowedUrl, sanitizeMarkdown } from "../lib/sanitizeMarkdown";
import { buildArticleBlocks } from "./adSlotPlan";
import AdSenseUnit from "./AdSenseUnit";

function textFromChildren(children) {
  if (children == null || typeof children === "boolean") return "";
  if (typeof children === "string" || typeof children === "number") return String(children);
  if (Array.isArray(children)) return children.map(textFromChildren).join("");
  if (children.props?.children) return textFromChildren(children.props.children);
  return "";
}

function headingComponent(level, headings) {
  const numeric = level === "h2" ? 2 : 3;
  const catalog = Array.isArray(headings) ? headings : [];
  const Tag = level;
  return function Heading({ node, children }) {
    const text = textFromChildren(children).replace(/\s+/g, " ").trim();
    const base = slugifyHeading(text);
    const line = node?.position?.start?.line;
    const match = catalog.find((item) => item.level === numeric && item.line === line);
    const id = match && slugifyHeading(match.text) === base ? match.id : base;
    return <Tag id={id}>{children}</Tag>;
  };
}

function SafeLink({ href, children }) {
  const url = allowedUrl(href);
  if (!url) return <span>{children}</span>;
  return <a href={url}>{children}</a>;
}

function SafeImage({ src, alt }) {
  const url = allowedUrl(src);
  if (!url || !/^https?:/i.test(url)) return null;
  return <img src={url} alt={alt || ""} />;
}

export default function ArticleView({
  markdown,
  isApproved = false,
  headingIds = null,
  plain = false,
}) {
  const blocks = buildArticleBlocks(
    stripPhotoCredits(sanitizeMarkdown(markdown)),
    isApproved === true,
  );
  const components = {
    h2: headingComponent("h2", headingIds),
    h3: headingComponent("h3", headingIds),
    a: SafeLink,
    img: SafeImage,
  };

  return (
    <div className={plain ? "markdown-body guide-copy" : "markdown-body"}>
      {blocks.map((block, index) =>
        block.kind === "ad" ? (
          <AdSenseUnit key={`${block.slot}-${index}`} slotId={block.slot} format="auto" />
        ) : (
          <ReactMarkdown key={`md-${index}`} remarkPlugins={[remarkGfm]} components={components}>
            {block.text}
          </ReactMarkdown>
        ),
      )}
    </div>
  );
}
