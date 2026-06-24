import { Node as ProseMirrorNode } from 'prosemirror-model';

import {
  ARTICLE_DOCUMENT_SCHEMA_VERSION,
  ArticleDocumentEnvelope,
  ArticleDocumentValidationIssue,
  ArticleDocumentValidationResult,
} from './ArticleDocumentTypes.js';
import { articleDocumentSchema } from './TiptapExtensionAllowlist.js';

export class ArticleDocumentValidator {
  validate(value: unknown): ArticleDocumentValidationResult {
    const errors: ArticleDocumentValidationIssue[] = [];

    if (!this.isRecord(value)) {
      return {
        valid: false,
        errors: [{ field: 'article', issue: 'article_document must be an object' }],
      };
    }

    const article = value as Partial<ArticleDocumentEnvelope>;

    if (article.schema_version !== ARTICLE_DOCUMENT_SCHEMA_VERSION) {
      errors.push({
        field: 'schema_version',
        issue: `Expected ${ARTICLE_DOCUMENT_SCHEMA_VERSION}`,
      });
    }

    if (!article.title || typeof article.title !== 'string') {
      errors.push({
        field: 'title',
        issue: 'Title is required',
      });
    }

    if (!this.isRecord(article.doc)) {
      errors.push({
        field: 'doc',
        issue: 'ProseMirror/Tiptap JSON doc is required',
      });
    } else {
      try {
        const node = ProseMirrorNode.fromJSON(articleDocumentSchema, article.doc);
        node.check();
      } catch (error) {
        errors.push({
          field: 'doc',
          issue: error instanceof Error ? error.message : 'Invalid document JSON',
        });
      }
    }

    this.validateImageNodes(article.doc, article.assets ?? {}, errors);

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  assertValid(value: unknown): asserts value is ArticleDocumentEnvelope {
    const result = this.validate(value);
    if (!result.valid) {
      const summary = result.errors.map((error) => `${error.field}: ${error.issue}`).join('; ');
      throw new Error(`Invalid article_document: ${summary}`);
    }
  }

  private validateImageNodes(
    node: unknown,
    assets: ArticleDocumentEnvelope['assets'],
    errors: ArticleDocumentValidationIssue[],
    path = 'doc'
  ): void {
    if (!this.isRecord(node)) {
      return;
    }

    if (node.type === 'image') {
      const attrs = this.isRecord(node.attrs) ? node.attrs : {};
      const assetRef = attrs.asset_ref;
      if (!assetRef || typeof assetRef !== 'string') {
        errors.push({
          field: `${path}.attrs.asset_ref`,
          issue: 'Image node must include asset_ref',
        });
      } else if (!assets?.[assetRef]) {
        errors.push({
          field: `assets.${assetRef}`,
          issue: 'Image asset_ref is not present in article assets',
        });
      }
    }

    if (Array.isArray(node.content)) {
      node.content.forEach((child, index) =>
        this.validateImageNodes(child, assets, errors, `${path}.content[${index}]`)
      );
    }
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }
}
