import { Schema } from 'prosemirror-model';

export const articleDocumentSchema = new Schema({
  nodes: {
    doc: {
      content: 'block+',
    },
    paragraph: {
      content: 'inline*',
      group: 'block',
    },
    heading: {
      content: 'inline*',
      group: 'block',
      attrs: {
        level: { default: 2 },
      },
    },
    horizontalRule: {
      group: 'block',
    },
    image: {
      group: 'block',
      atom: true,
      attrs: {
        asset_ref: {},
        alt: { default: null },
        title: { default: null },
      },
    },
    text: {
      group: 'inline',
    },
    hardBreak: {
      inline: true,
      group: 'inline',
      selectable: false,
    },
  },
  marks: {
    bold: {},
    strong: {},
    link: {
      attrs: {
        href: {},
        title: { default: null },
      },
      inclusive: false,
    },
  },
});

export const ARTICLE_DOCUMENT_ALLOWED_NODES = Object.freeze(
  Object.keys(articleDocumentSchema.nodes)
);

export const ARTICLE_DOCUMENT_ALLOWED_MARKS = Object.freeze(
  Object.keys(articleDocumentSchema.marks)
);
