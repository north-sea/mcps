import {
  ARTICLE_DOCUMENT_SCHEMA_VERSION,
  ArticleDocumentAsset,
  ArticleDocumentCover,
  ArticleDocumentEnvelope,
} from './ArticleDocumentTypes.js';
import { ArticleDocumentValidator } from './ArticleDocumentValidator.js';

type InlineNode = {
  type: 'text';
  text: string;
  marks?: Array<{ type: 'bold' }>;
};

type BlockNode =
  | { type: 'heading'; attrs: { level: number }; content: InlineNode[] }
  | { type: 'paragraph'; content: InlineNode[] }
  | { type: 'image'; attrs: { asset_ref: string; alt?: string } }
  | { type: 'horizontalRule' };

export interface ImportMarkdownArticleInput {
  markdown: string;
  title?: string;
  digest?: string;
  author?: string;
  style_profile_id?: string;
  content_source_url?: string;
  cover?: ArticleDocumentCover;
  body_images?: ArticleDocumentAsset[];
  source_markdown_artifact_id?: string;
  parent_artifact_id?: string;
}

export class MarkdownArticleImporter {
  private validator: ArticleDocumentValidator = new ArticleDocumentValidator();

  import(input: ImportMarkdownArticleInput): ArticleDocumentEnvelope {
    const lines = this.stripFrontmatter(input.markdown).split(/\r?\n/);
    const assets: Record<string, ArticleDocumentAsset> = {};
    const blocks: BlockNode[] = [];
    let imageIndex = 0;
    let title = input.title;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        continue;
      }

      const h1 = line.match(/^#\s+(.+)$/);
      if (h1) {
        title ||= this.stripInlineMarkdown(h1[1]);
        continue;
      }

      const heading = line.match(/^(#{2,6})\s+(.+)$/);
      if (heading) {
        blocks.push({
          type: 'heading',
          attrs: { level: Math.min(heading[1].length, 3) },
          content: this.parseInline(heading[2]),
        });
        continue;
      }

      if (line === '* * *' || line === '---') {
        blocks.push({ type: 'horizontalRule' });
        continue;
      }

      const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (image) {
        const asset = input.body_images?.[imageIndex];
        if (!asset) {
          throw new Error(`Missing prepared image asset for Markdown image: ${image[2]}`);
        }
        assets[asset.asset_ref] = {
          ...asset,
          alt: asset.alt || this.stripInlineMarkdown(image[1]) || undefined,
        };
        blocks.push({
          type: 'image',
          attrs: {
            asset_ref: asset.asset_ref,
            alt: assets[asset.asset_ref].alt,
          },
        });
        imageIndex += 1;
        continue;
      }

      blocks.push({
        type: 'paragraph',
        content: this.parseInline(line),
      });
    }

    const article: ArticleDocumentEnvelope = {
      schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
      title: title || 'Untitled',
      digest: input.digest,
      author: input.author,
      style_profile_id: input.style_profile_id,
      content_source_url: input.content_source_url,
      cover: input.cover,
      assets,
      doc: {
        type: 'doc',
        content: blocks,
      },
      source_markdown_artifact_id: input.source_markdown_artifact_id,
      parent_artifact_id: input.parent_artifact_id,
    };

    this.validator.assertValid(article);
    return article;
  }

  private parseInline(value: string): InlineNode[] {
    const nodes: InlineNode[] = [];
    const pattern = /\*\*([^*]+)\*\*/g;
    let offset = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(value)) !== null) {
      if (match.index > offset) {
        nodes.push({ type: 'text', text: value.slice(offset, match.index) });
      }
      nodes.push({
        type: 'text',
        text: match[1],
        marks: [{ type: 'bold' }],
      });
      offset = match.index + match[0].length;
    }

    if (offset < value.length) {
      nodes.push({ type: 'text', text: value.slice(offset) });
    }

    return nodes.filter((node) => node.text.length > 0);
  }

  private stripFrontmatter(markdown: string): string {
    return markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  }

  private stripInlineMarkdown(value: string): string {
    return value
      .replace(/^#{1,6}\s+/, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  }
}
