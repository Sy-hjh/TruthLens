const FILE_LABEL = /^(?:的\s*)?(?:有(?:一)?个\s*)?(?:(?:文件名|文件|名字)\s*)?(?:叫(?:做)?|名称\s*[:：]?|名为|是)\s*[:：]?\s*/;
const FOLLOW_UP = /(?:你去|你帮我|帮我|请(?:你)?|麻烦你)(?=找|查|读|打开|核验|鉴别|检测)/;

export function localFileReference(text: string, pendingLocation = ""): { filename: string; location: string } | null {
  const location = /(?<![a-z0-9])([a-z])\s*盘(?:里|中|上)?|(?:放在|保存在|存放在|存于|位于|在)\s*(?:电脑)?桌面(?:上)?|(?:^|[，,。\s])桌面(?:上)?(?=$|\s|[，,。]|叫|的|文件)/i.exec(text);
  if ((!location && !pendingLocation) || /(?:别|不要|不用|不必)(?:帮我|去)?(?:再)?(?:查|读|找|打开|检测|核验|鉴别)|^(?:不用了|算了|取消)[。！!\s]*$/.test(text)) return null;
  const tail = (location ? text.slice(location.index + location[0].length) : text).trim().replace(/^[，,。\s]+/, "");
  const label = FILE_LABEL.exec(tail);
  const named = tail.slice(label?.[0].length ?? 0).replace(/^的\s*/, "").trim();
  const quoted = /^[“"「]([^”"」\r\n]+)[”"」]/.exec(named);
  const unquoted = named.split(/[，,。！？；!?;、\r\n]/, 1)[0].split(FOLLOW_UP, 1)[0];
  const raw = (quoted?.[1] ?? unquoted.trim().replace(/(?:\s+|(?<=[a-z0-9]))的(?:录音|语音|音频|视频|图片|文件)$/i, "")).trim();
  if (!location && !label && !quoted && /[，,。！？；!?;、\r\n]/.test(tail) && !/\.[a-z0-9]{2,5}$/i.test(raw)) return null;
  const filename = /^[^\\/:*?"<>|\u0000-\u001f]{1,255}$/.test(raw) &&
    (label || quoted || pendingLocation || /\.[a-z0-9]{2,5}$/i.test(raw)) ? raw : "";
  return { filename, location: location ? (location[1] ? location[1].toUpperCase() + "盘" : "desktop") : pendingLocation };
}
