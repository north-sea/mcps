/**
 * Manual tests for MarkdownWechatRenderer.
 */

import { MarkdownWechatRenderer, getWechatStyleProfile } from './dist/render/index.js';

let testCount = 0;
let passCount = 0;

function assert(condition, message) {
  testCount++;
  if (!condition) {
    console.error(`FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passCount++;
  console.log(`PASS: ${message}`);
}

function render(markdown) {
  return new MarkdownWechatRenderer().render({
    markdown,
    profile: getWechatStyleProfile('weiyuchengchun.default'),
    include_cover_image: { wechat_url: 'https://mmbiz.qpic.cn/mock-cover', alt: 'cover' },
    body_images: [
      { wechat_url: 'https://mmbiz.qpic.cn/mock-body1', alt: '插图1' },
      { wechat_url: 'https://mmbiz.qpic.cn/mock-body2', alt: '插图2' },
    ],
  }).html;
}

function assertTitleAlternativesStripped(markdown, label) {
  const html = render(markdown);
  assert(html.includes('正文保留'), `${label}: keeps article body`);
  assert(!html.includes('标题备选'), `${label}: strips title alternatives heading`);
  assert(!html.includes('未选用'), `${label}: strips title alternatives metadata`);
  assert(!html.includes('方案一'), `${label}: strips title alternatives list`);
}

assertTitleAlternativesStripped(
  `# 标题

正文保留

---

标题备选：
- 方案一`,
  'plain title alternatives'
);

assertTitleAlternativesStripped(
  `# 标题

正文保留

---
**标题备选**（未选用）：
1. 方案一`,
  'bold title alternatives with suffix'
);

assertTitleAlternativesStripped(
  `# 标题

正文保留

## 标题备选
1. 方案一`,
  'heading title alternatives'
);

{
  const html = render(`# 标题

## 小标题

正文保留`);
  assert(!html.includes('## 小标题'), 'markdown h2 marker is stripped');
  assert(html.includes('小标题'), 'markdown h2 text is rendered');
  assert(html.includes('正文保留'), 'body after h2 is rendered');
}

{
  const html = new MarkdownWechatRenderer().render({
    markdown: `# 标题

![图片里的 **强调** 文本](https://example.com/image.png)`,
    profile: getWechatStyleProfile('weiyuchengchun.default'),
    body_images: [{ wechat_url: 'https://mmbiz.qpic.cn/mock-body1' }],
  }).html;
  assert(html.includes('alt="图片里的 强调 文本"'), 'markdown markers are stripped from image alt text');
  assert(!html.includes('**强调**'), 'raw bold markers are not kept in image alt text');
}

console.log(`\n${passCount}/${testCount} tests passed`);
