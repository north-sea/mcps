import { ArticleDocumentEnvelope } from './ArticleDocumentTypes.js';
import { ArticleDocumentValidator } from './ArticleDocumentValidator.js';
import { WechatArticleDocumentRenderer } from './WechatArticleDocumentRenderer.js';
import { getWechatStyleProfile } from './WechatStyleProfile.js';

type JsonNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: Array<{ type?: string; attrs?: Record<string, unknown> }>;
  content?: JsonNode[];
};

export interface ExportMarkdownArticleResult {
  markdown: string;
  non_canonical: true;
  warnings: string[];
}

export interface ExportHtmlPreviewResult {
  html: string;
  non_canonical: true;
  warnings: string[];
}

export class MarkdownArticleExporter {
  private validator: ArticleDocumentValidator = new ArticleDocumentValidator();

  exportMarkdown(article: ArticleDocumentEnvelope): ExportMarkdownArticleResult {
    this.validator.assertValid(article);

    const lines: string[] = [
      '<!-- non-canonical preview: generated from article_document; possibly lossy -->',
      `# ${article.title}`,
      '',
    ];

    for (const child of this.rootContent(article)) {
      const rendered = this.renderMarkdownNode(child, article);
      if (rendered) {
        lines.push(rendered, '');
      }
    }

    return {
      markdown: lines.join('\n').trimEnd() + '\n',
      non_canonical: true,
      warnings: ['Markdown is a non-canonical preview/export format. Use article_document as source of truth.'],
    };
  }

  exportHtmlPreview(article: ArticleDocumentEnvelope): ExportHtmlPreviewResult {
    this.validator.assertValid(article);
    const profile = getWechatStyleProfile(article.style_profile_id || 'yueliang.default');
    const html = new WechatArticleDocumentRenderer(profile).render({ article }).html;
    return {
      html: `<!-- non-canonical preview: generated from article_document; possibly lossy -->${html}`,
      non_canonical: true,
      warnings: ['HTML preview is derived from article_document and should not replace wechat_api_article.'],
    };
  }

  private rootContent(article: ArticleDocumentEnvelope): JsonNode[] {
    const doc = article.doc as JsonNode;
    return Array.isArray(doc.content) ? doc.content : [];
  }

  private renderMarkdownNode(node: JsonNode, article: ArticleDocumentEnvelope): string {
    switch (node.type) {
      case 'paragraph':
        return this.renderInlineContent(node);
      case 'heading': {
        const level = typeof node.attrs?.level === 'number' ? node.attrs.level : 2;
        return `${'#'.repeat(Math.min(Math.max(level, 2), 6))} ${this.renderInlineContent(node)}`;
      }
      case 'horizontalRule':
        return '---';
      case 'image': {
        const assetRef = typeof node.attrs?.asset_ref === 'string' ? node.attrs.asset_ref : '';
        const asset = assetRef ? article.assets?.[assetRef] : undefined;
        const alt =
          typeof node.attrs?.alt === 'string'
            ? node.attrs.alt
            : asset?.alt || 'image';
        return `![${this.escapeMarkdownAlt(alt)}](${asset?.wechat_url || assetRef})`;
      }
      default:
        throw new Error(`Unsupported article_document node: ${node.type ?? 'unknown'}`);
    }
  }

  private renderInlineContent(node: JsonNode): string {
    return (node.content ?? []).map((child) => this.renderInlineNode(child)).join('');
  }

  private renderInlineNode(node: JsonNode): string {
    if (node.type === 'text') {
      return this.applyMarkdownMarks(node.text ?? '', node.marks ?? []);
    }

    if (node.type === 'hardBreak') {
      return '  \n';
    }

    throw new Error(`Unsupported inline article_document node: ${node.type ?? 'unknown'}`);
  }

  private applyMarkdownMarks(
    value: string,
    marks: Array<{ type?: string; attrs?: Record<string, unknown> }>
  ): string {
    return marks.reduce((current, mark) => {
      if (mark.type === 'bold' || mark.type === 'strong') {
        return `**${current}**`;
      }

      if (mark.type === 'link') {
        const href = typeof mark.attrs?.href === 'string' ? mark.attrs.href : '';
        return `[${current}](${href})`;
      }

      throw new Error(`Unsupported article_document mark: ${mark.type ?? 'unknown'}`);
    }, value);
  }

  private escapeMarkdownAlt(value: string): string {
    return value.replaceAll('[', '\\[').replaceAll(']', '\\]');
  }
}
