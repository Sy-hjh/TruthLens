"""Server-side configuration and client for a compatible chat endpoint."""

import json
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests

from bootstrap import ROOT


CONFIG_FILE = ROOT / 'runtime' / 'companion-model.json'


class OnlineModelError(RuntimeError):
    pass


@dataclass(frozen=True)
class OnlineModel:
    endpoint: str
    model: str
    api_key: str = field(repr=False)

    def generate(self, messages, *, structured_answer=False):
        payload = {'model': self.model, 'messages': messages, 'stream': False}
        native_structured_output = self.model == 'XingChenAGI/Xing4.0-29B' and urlsplit(self.endpoint).hostname == 'api.siliconflow.cn'
        if native_structured_output:
            payload['enable_thinking'] = False
        if structured_answer and native_structured_output:
            payload['response_format'] = {
                'type': 'json_schema',
                'json_schema': {
                    'name': 'companion_answer',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {'answer': {'type': 'string'}},
                        'required': ['answer'],
                        'additionalProperties': False,
                    },
                },
            }
        try:
            response = requests.post(
                self.endpoint,
                headers={'Authorization': f'Bearer {self.api_key}'},
                json=payload,
                timeout=(5, 65),
                allow_redirects=False,
            )
        except requests.Timeout:
            raise OnlineModelError('在线模型响应超时，请重试。') from None
        except requests.RequestException:
            raise OnlineModelError('无法连接在线模型，请核对接口地址和网络。') from None
        if response.status_code in (401, 403):
            raise OnlineModelError('在线模型拒绝认证，请检查 API Key 和权限。')
        if response.status_code == 429:
            raise OnlineModelError('在线模型请求受限，请检查额度或稍后重试。')
        if response.status_code != 200:
            raise OnlineModelError(f'在线模型接口返回 HTTP {response.status_code}，请检查接口地址和模型名。')
        try:
            text = response.json()['choices'][0]['message']['content']
        except (ValueError, KeyError, IndexError, TypeError):
            raise OnlineModelError('在线接口的响应格式无法读取，请使用兼容 Chat Completions 的接口。') from None
        if not isinstance(text, str) or not text.strip():
            raise OnlineModelError('在线模型未返回文字，请检查模型设置。')
        return text


def configured_model():
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise OnlineModelError('无法读取在线模型配置，请检查 companion-model.json。') from None

    keys = ('base_url', 'model', 'api_key')
    if not isinstance(config, dict) or any(not isinstance(config.get(key), str) for key in keys):
        raise OnlineModelError('在线模型配置需要 base_url、model 和 api_key 三个文本字段。')
    enabled = config.get('enabled', True)
    if not isinstance(enabled, bool):
        raise OnlineModelError('在线模型配置中的 enabled 应为 true 或 false。')
    if not enabled:
        return None
    base_url, model, api_key = (config[key].strip() for key in keys)
    if not any((base_url, model, api_key)):
        return None
    if not all((base_url, model, api_key)):
        raise OnlineModelError('请在在线模型配置中填齐接口地址、模型名和 API Key。')
    try:
        url = urlsplit(base_url)
        secure = url.scheme == 'https' or (url.scheme == 'http' and url.hostname in {'127.0.0.1', 'localhost', '::1'})
        if not secure or not url.hostname or url.username is not None or url.query or url.fragment or any(char.isspace() for char in base_url):
            raise ValueError
    except ValueError:
        raise OnlineModelError('请输入有效的 HTTPS 接口地址。') from None
    if any(not 33 <= ord(char) <= 126 for char in api_key):
        raise OnlineModelError('API Key 包含无效字符，请重新复制。')
    endpoint = base_url.rstrip('/')
    if not endpoint.endswith('/chat/completions'):
        endpoint += '/chat/completions'
    return OnlineModel(endpoint, model, api_key)
