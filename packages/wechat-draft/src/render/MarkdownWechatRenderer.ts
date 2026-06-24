import { WechatStyleProfile } from './WechatStyleProfile.js';

export interface MarkdownImageAsset {
  wechat_url: string;
  alt?: string;
}

export interface RenderMarkdownInput {
  markdown: string;
  profile: WechatStyleProfile;
  body_images: MarkdownImageAsset[];
  include_cover_image?: MarkdownImageAsset;
}

export interface RenderMarkdownOutput {
  html: string;
  consumed_body_images: number;
}

export class MarkdownWechatRenderer {
  render(input: RenderMarkdownInput): RenderMarkdownOutput {
    const body = this.stripFrontmatter(input.markdown);
    const main = this.stripTitleAlternatives(body);
    const lines = main.split(/\r?\n/);
    const fragments: string[] = [];
    let imageIndex = 0;

    if (input.include_cover_image) {
      fragments.push(this.renderImageSection(input.include_cover_image, input.profile));
    }

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        continue;
      }

      if (line.startsWith('# ')) {
        continue;
      }

      const headingMatch = line.match(/^#{2,6}\s+(.+)$/);
      if (headingMatch) {
        fragments.push(this.renderHeading(headingMatch[1], input.profile));
        continue;
      }

      if (line === '* * *' || line === '---') {
        fragments.push(`<hr style="${input.profile.divider_style}" />`);
        continue;
      }

      const imageMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imageMatch) {
        const image = input.body_images[imageIndex];
        if (!image) {
          throw new Error(`Missing uploaded WeChat body image for markdown image: ${imageMatch[2]}`);
        }
        fragments.push(this.renderImageSection({ ...image, alt: image.alt || imageMatch[1] }, input.profile));
        imageIndex += 1;
        continue;
      }

      fragments.push(
        `<p style="${input.profile.paragraph_style}"><span leaf="">${this.renderInlineMarkdown(line, input.profile)}</span></p>`
      );
    }

    return {
      html: `<section style="${input.profile.container_style}" data-pm-slice="0 0 []">${fragments.join('')}</section>`,
      consumed_body_images: imageIndex,
    };
  }

  private renderImageSection(image: MarkdownImageAsset, profile: WechatStyleProfile): string {
    const alt = this.escapeAttribute(this.stripInlineMarkdown(image.alt || 'image'));
    const src = this.escapeAttribute(image.wechat_url);
    return `<section style="${profile.image_section_style}" nodeleaf=""><img alt="${alt}" class="rich_pages wxw-img" data-src="${src}" style="${profile.image_style}" src="${src}" /></section>`;
  }

  private renderHeading(text: string, profile: WechatStyleProfile): string {
    const style = profile.heading_style ?? `${profile.paragraph_style}${profile.strong_style}`;
    return `<p style="${style}"><span leaf="">${this.renderInlineMarkdown(text, profile)}</span></p>`;
  }

  private stripFrontmatter(markdown: string): string {
    return markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  }

  private stripTitleAlternatives(markdown: string): string {
    return markdown.replace(
      /\r?\n(?:\s*(?:---|\* \* \*)\s*\r?\n)?\s*(?:#{1,6}\s*)?(?:\*\*)?标题备选(?:\*\*)?(?:[（(][^）)]*[）)])?\s*[:：]?[\s\S]*$/,
      ''
    );
  }

  private renderInlineMarkdown(line: string, profile: WechatStyleProfile): string {
    const escaped = this.escapeHtml(line);
    return escaped.replace(/\*\*([^*]+)\*\*/g, `<strong style="${profile.strong_style}">$1</strong>`);
  }

  private stripInlineMarkdown(value: string): string {
    return value
      .replace(/^#{1,6}\s+/, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
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
