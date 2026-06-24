export interface WechatStyleProfile {
  profile_id: string;
  account_id: string;
  version: string;
  container_style: string;
  paragraph_style: string;
  image_section_style: string;
  image_style: string;
  divider_style: string;
  strong_style: string;
  heading_style?: string;
  hidden_paragraph_style?: string;
}

export const WEIYUCHENGCHUN_DEFAULT_PROFILE: WechatStyleProfile = {
  profile_id: 'weiyuchengchun.default',
  account_id: 'weiyuchengchun',
  version: '2026-06-22-from-manual-draft',
  container_style:
    'max-width: 720px;margin: 0 auto;padding: 8px;font-family: PingFang SC,system-ui,-apple-system,BlinkMacSystemFont,Helvetica Neue,Hiragino Sans GB,Microsoft YaHei UI,Microsoft YaHei,Arial,sans-serif;font-size: 16px;line-height: 1.75 !important;font-weight: 400;color: #2c2c2c !important;text-align: left !important;overflow-wrap: break-word;word-wrap: break-word;',
  paragraph_style: 'margin: 5px 0 20px !important;',
  image_section_style: 'margin: 5px 0 20px !important;',
  image_style: 'max-width: 100%;max-height: 600px !important;height: auto;display: block;margin: 32px auto;',
  divider_style: 'margin: 3rem 0;border: none;height: 1px;background-color: rgba(43, 174, 133, 0.2);',
  strong_style: 'font-weight: 700;color: #2BAE85 !important;',
  heading_style: 'margin: 34px 0 18px !important;font-size: 18px;line-height: 1.6 !important;font-weight: 700;color: #2BAE85 !important;',
  hidden_paragraph_style: 'display: none',
};

export const YUELIANG_DEFAULT_PROFILE: WechatStyleProfile = {
  profile_id: 'yueliang.default',
  account_id: 'yueliang',
  version: '2026-06-24-from-yueliang-styled-draft',
  container_style:
    'max-width: 720px;margin: 0 auto;padding: 8px;font-family: PingFang SC,system-ui,-apple-system,BlinkMacSystemFont,Helvetica Neue,Hiragino Sans GB,Microsoft YaHei UI,Microsoft YaHei,Arial,sans-serif;font-size: 16px;line-height: 1.75 !important;font-weight: 400;color: #2c2c2c !important;text-align: left !important;overflow-wrap: break-word;word-wrap: break-word;',
  paragraph_style: 'margin: 5px 0 20px !important;',
  image_section_style: 'margin: 5px 0 20px !important;',
  image_style:
    'max-width: 100%;max-height: 600px !important;height: auto;display: block;margin: 28px auto;border-radius: 6px;border: 1px solid rgba(78, 89, 105, 0.1);box-shadow: 0 2px 8px rgba(78, 89, 105, 0.06), 0 8px 24px rgba(78, 89, 105, 0.08);',
  divider_style:
    'margin: 2.5rem auto;border: none;height: 1px;width: 50%;background: linear-gradient(to right, transparent, rgba(78, 89, 105, 0.3), rgba(78, 89, 105, 0.3), transparent);',
  strong_style: 'font-weight: 600;color: #4E5969 !important;',
  heading_style:
    'font-size: 22px;font-weight: 700;color: #4E5969 !important;margin-top: 36px !important;margin-bottom: 24px !important;line-height: 1.4em !important;overflow-wrap: break-word;word-wrap: break-word;padding-left: 18px;letter-spacing: 0.03em;background-image: linear-gradient(#4E5969, #4E5969), linear-gradient(rgba(78, 89, 105, 0.32), rgba(78, 89, 105, 0.32));background-size: 2px 70%, 1px 92%;background-position: left center, 6px center;background-repeat: no-repeat;',
  hidden_paragraph_style: 'display: none;',
};

const STYLE_PROFILES = new Map<string, WechatStyleProfile>([
  [WEIYUCHENGCHUN_DEFAULT_PROFILE.profile_id, WEIYUCHENGCHUN_DEFAULT_PROFILE],
  [YUELIANG_DEFAULT_PROFILE.profile_id, YUELIANG_DEFAULT_PROFILE],
]);

export function getWechatStyleProfile(profileId: string): WechatStyleProfile {
  const profile = STYLE_PROFILES.get(profileId);
  if (!profile) {
    throw new Error(`Unknown WeChat style profile: ${profileId}`);
  }
  return profile;
}
