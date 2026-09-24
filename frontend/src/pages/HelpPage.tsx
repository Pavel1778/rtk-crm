import { FilePdfOutlined, SearchOutlined } from '@ant-design/icons';
import {
  App as AntApp,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Space,
  Spin,
  Tabs,
  Typography,
} from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { Title, Text } = Typography;

interface DocTab {
  key: string;
  label: string;
  filename: string;
  pdf: string;
}

const DOC_TABS: DocTab[] = [
  {
    key: 'user',
    label: 'Руководство пользователя',
    filename: 'USER_GUIDE.md',
    pdf: 'user-guide.pdf',
  },
  {
    key: 'admin',
    label: 'Руководство администратора',
    filename: 'ADMIN_GUIDE.md',
    pdf: 'admin-guide.pdf',
  },
  { key: 'security', label: 'Безопасность', filename: 'SECURITY.md', pdf: '' },
  { key: 'architecture', label: 'Архитектура', filename: 'ARCHITECTURE.md', pdf: '' },
];

interface Section {
  id: string;
  label: string;
}

// Slug транслитерируем: якоря в адресной строке остаются читаемыми.
// Префикс `section-` обязателен: id не может начинаться с цифры, иначе
// querySelector('#3-vhod-...') падает с SyntaxError.
const SECTION_PREFIX = 'section-';

const TRANSLIT: Record<string, string> = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z',
  и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r',
  с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'sch',
  ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya', ' ': '-',
};

function slugify(text: string): string {
  let out = '';
  for (const char of text.toLowerCase()) {
    out += TRANSLIT[char] ?? char;
  }
  const slug = out
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return slug ? `${SECTION_PREFIX}${slug}` : '';
}

function extractSections(markdown: string): Section[] {
  const sections: Section[] = [];
  for (const line of markdown.split('\n')) {
    if (!line.startsWith('## ')) continue;
    const label = line.slice(3).trim();
    const id = slugify(label);
    if (id) sections.push({ id, label });
  }
  return sections;
}

function downloadStaticFile(path: string, filename: string): void {
  const anchor = document.createElement('a');
  anchor.href = path;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

export default function HelpPage() {
  const { message } = AntApp.useApp();
  const [content, setContent] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('user');
  const [query, setQuery] = useState('');
  const docRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      const entries = await Promise.all(
        DOC_TABS.map(async (tab) => {
          try {
            const response = await fetch(`/docs/${tab.filename}`);
            if (!response.ok) throw new Error('missing');
            return [tab.key, await response.text()] as const;
          } catch {
            return [tab.key, '# Документ не найден'] as const;
          }
        })
      );
      setContent(Object.fromEntries(entries));
      setLoading(false);
    };
    void loadAll();
  }, []);

  const currentDoc = content[activeTab] ?? '';
  const sections = useMemo(() => extractSections(currentDoc), [currentDoc]);
  const activeTabMeta = DOC_TABS.find((tab) => tab.key === activeTab);

  const scrollTo = useCallback((id: string) => {
    docRef.current?.querySelector(`#${id}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }, []);

  // Поиск идёт по заголовкам разделов: полнотекстовый фильтр разорвал бы
  // Markdown-разметку и сломал списки с таблицами.
  const matchedSections = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return sections;
    return sections.filter((section) => section.label.toLowerCase().includes(needle));
  }, [sections, query]);

  const tabItems = DOC_TABS.map((tab) => ({
    key: tab.key,
    label: tab.label,
    children: (
      <div style={{ padding: 16 }}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <Typography.Title level={3}>{children}</Typography.Title>
            ),
            h2: ({ children }) => (
              <Typography.Title
                level={4}
                id={slugify(String(children))}
                style={{ scrollMarginTop: 16, marginTop: 20 }}
              >
                {children}
              </Typography.Title>
            ),
            h3: ({ children }) => (
              <Typography.Title level={5} style={{ marginTop: 16 }}>
                {children}
              </Typography.Title>
            ),
            // react-markdown оборачивает одиночную картинку в <p>, и <figure>
            // внутри абзаца — невалидный DOM. Для таких абзацев отдаём
            // содержимое как есть, остальные абзацы рендерим обычным <p>.
            p: ({ node, children }) => {
              const only =
                node?.children?.length === 1 &&
                node.children[0].type === 'element' &&
                node.children[0].tagName === 'img';
              return only ? <>{children}</> : <p>{children}</p>;
            },
            img: ({ src, alt }) => (
              <figure style={{ margin: '12px 0' }}>
                <img
                  src={src}
                  alt={alt ?? ''}
                  loading="lazy"
                  // Скриншоты в руководствах — 1440×900. Явные размеры дают
                  // браузеру соотношение сторон, поэтому место резервируется
                  // до загрузки (нет сдвига вёрстки, CLS).
                  width={1440}
                  height={900}
                  style={{
                    maxWidth: '100%',
                    height: 'auto',
                    border: '1px solid var(--atmr-border-soft)',
                    borderRadius: 8,
                  }}
                />
                {alt ? (
                  <figcaption style={{ textAlign: 'center', marginTop: 6 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {alt}
                    </Text>
                  </figcaption>
                ) : null}
              </figure>
            ),
          }}
        >
          {content[tab.key] ?? ''}
        </ReactMarkdown>
      </div>
    ),
  }));

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>Помощь</Title>
      <Card style={{ border: '1px solid var(--atmr-border-soft)' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Row gutter={24}>
            <Col xs={24} md={7} lg={6}>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <Input
                  allowClear
                  prefix={<SearchOutlined />}
                  placeholder="Поиск по разделам"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <div style={{ maxHeight: 420, overflowY: 'auto' }}>
                  {matchedSections.length ? (
                    matchedSections.map((section) => (
                      <div
                        key={section.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => scrollTo(section.id)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') scrollTo(section.id);
                        }}
                        style={{ padding: '6px 4px', cursor: 'pointer' }}
                      >
                        <Text>{section.label}</Text>
                      </div>
                    ))
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="Разделы не найдены"
                    />
                  )}
                </div>
                {activeTabMeta?.pdf ? (
                  <Button
                    icon={<FilePdfOutlined />}
                    onClick={() => {
                      downloadStaticFile(`/docs/${activeTabMeta.pdf}`, activeTabMeta.pdf);
                      message.success('PDF-версия руководства скачивается');
                    }}
                    block
                  >
                    Скачать PDF
                  </Button>
                ) : null}
              </Space>
            </Col>
            <Col xs={24} md={17} lg={18}>
              <div ref={docRef} className="help-doc">
                <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
              </div>
            </Col>
          </Row>
        )}
      </Card>
    </div>
  );
}
