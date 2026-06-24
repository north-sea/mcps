import {
  ArticleDocumentAsset,
  ArticleDocumentEnvelope,
  RenderArticleDocumentInput,
  RenderArticleDocumentOutput,
} from './ArticleDocumentTypes.js';
import { ArticleDocumentValidator } from './ArticleDocumentValidator.js';
import { WechatStyleProfile } from './WechatStyleProfile.js';

type JsonNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: Array<{ type?: string; attrs?: Record<string, unknown> }>;
  content?: JsonNode[];
};

export class WechatArticleDocumentRenderer {
  private validator: ArticleDocumentValidator = new ArticleDocumentValidator();

  constructor(private profile: WechatStyleProfile) {}

  render(input: RenderArticleDocumentInput): RenderArticleDocumentOutput {
    this.validator.assertValid(input.article);

    const assets = {
      ...(input.article.assets ?? {}),
      ...(input.assets ?? {}),
    };
    const consumedBodyImages: RenderArticleDocumentOutput['consumed_body_images'] = [];
    const fragments: string[] = [];

    if (input.include_cover_image && input.article.cover?.asset_ref) {
      const cover = this.resolveImageAsset(input.article.cover.asset_ref, assets);
      fragments.push(this.renderImageSection(cover, input.article.cover.alt));
    }

    for (const child of this.rootContent(input.article)) {
      const rendered = this.renderNode(child, input.article, assets, consumedBodyImages);
      if (rendered) {
        fragments.push(rendered);
      }
    }

    return {
      html: `<section style="${this.profile.container_style}" data-pm-slice="0 0 []">${fragments.join('')}</section>`,
      consumed_body_images: consumedBodyImages,
    };
  }

  private rootContent(article: ArticleDocumentEnvelope): JsonNode[] {
    const doc = article.doc as JsonNode;
    return Array.isArray(doc.content) ? doc.content : [];
  }

  private renderNode(
    node: JsonNode,
    article: ArticleDocumentEnvelope,
    assets: Record<string, ArticleDocumentAsset>,
    consumedBodyImages: RenderArticleDocumentOutput['consumed_body_images']
  ): string {
    switch (node.type) {
      case 'paragraph':
        return this.renderParagraph(node);
      case 'heading':
        return this.renderHeading(node);
      case 'horizontalRule':
        return `<hr style="${this.profile.divider_style}" />`;
      case 'image': {
        const assetRef = this.stringAttr(node, 'asset_ref');
        if (!assetRef) {
          throw new Error('Image node must include asset_ref');
        }
        const asset = this.resolveImageAsset(assetRef, assets);
        consumedBodyImages.push({ asset_ref: assetRef, wechat_url: asset.wechat_url as string });
        return this.renderImageSection(asset, this.stringAttr(node, 'alt'));
      }
      default:
        throw new Error(`Unsupported article_document node: ${node.type ?? 'unknown'}`);
    }
  }

  private renderParagraph(node: JsonNode): string {
    const content = this.renderInlineContent(node);
    if (!content) {
      return '';
    }
    return `<p style="${this.profile.paragraph_style}"><span leaf="">${content}</span></p>`;
  }

  private renderHeading(node: JsonNode): string {
    const content = this.renderInlineContent(node);
    if (!content) {
      return '';
    }
    const style = this.profile.heading_style ?? `${this.profile.paragraph_style}${this.profile.strong_style}`;
    return `<p style="${style}"><span leaf="">${content}</span></p>`;
  }

  private renderInlineContent(node: JsonNode): string {
    return (node.content ?? []).map((child) => this.renderInlineNode(child)).join('');
  }

  private renderInlineNode(node: JsonNode): string {
    if (node.type === 'text') {
      return this.applyMarks(this.escapeHtml(node.text ?? ''), node.marks ?? []);
    }

    if (node.type === 'hardBreak') {
      return '<br />';
    }

    throw new Error(`Unsupported inline article_document node: ${node.type ?? 'unknown'}`);
  }

  private applyMarks(
    value: string,
    marks: Array<{ type?: string; attrs?: Record<string, unknown> }>
  ): string {
    return marks.reduce((current, mark) => {
      if (mark.type === 'bold' || mark.type === 'strong') {
        return `<strong style="${this.profile.strong_style}">${current}</strong>`;
      }

      if (mark.type === 'link') {
        const href = typeof mark.attrs?.href === 'string' ? mark.attrs.href : '';
        if (!href.startsWith('https://') && !href.startsWith('http://')) {
          throw new Error(`Unsupported link href: ${href || 'missing'}`);
        }
        const title =
          typeof mark.attrs?.title === 'string'
            ? ` title="${this.escapeAttribute(mark.attrs.title)}"`
            : '';
        return `<a href="${this.escapeAttribute(href)}"${title}>${current}</a>`;
      }

      throw new Error(`Unsupported article_document mark: ${mark.type ?? 'unknown'}`);
    }, value);
  }

  private resolveImageAsset(
    assetRef: string,
    assets: Record<string, ArticleDocumentAsset>
  ): ArticleDocumentAsset {
    const asset = assets[assetRef];
    if (!asset) {
      throw new Error(`Image asset is missing: ${assetRef}`);
    }

    if (asset.ready === false) {
      throw new Error(`Image asset is not ready: ${assetRef}`);
    }

    if (!asset.wechat_url || !this.isWechatImageUrl(asset.wechat_url)) {
      throw new Error(`Image asset must use a WeChat image URL: ${assetRef}`);
    }

    return asset;
  }

  private renderImageSection(asset: ArticleDocumentAsset, fallbackAlt?: string): string {
    const alt = this.escapeAttribute(asset.alt || fallbackAlt || 'image');
    const src = this.escapeAttribute(asset.wechat_url as string);
    return `<section style="${this.profile.image_section_style}" nodeleaf=""><img alt="${alt}" class="rich_pages wxw-img" data-src="${src}" style="${this.profile.image_style}" src="${src}" /></section>`;
  }

  private stringAttr(node: JsonNode, name: string): string | undefined {
    const value = node.attrs?.[name];
    return typeof value === 'string' ? value : undefined;
  }

  private isWechatImageUrl(url: string): boolean {
    return url.startsWith('https://mmbiz.qpic.cn/') || url.startsWith('http://mmbiz.qpic.cn/');
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;');
  }

  private escapeAttribute(value: string): string {
    return this.escapeHtml(value).replaceAll('"', '&quot;');
  }
}
