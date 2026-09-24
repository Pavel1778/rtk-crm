/**
 * Экспорт DOM-узла (диаграммы recharts) в PNG или PDF.
 *
 * Диаграммы остаются интерактивными: экспортируется текущее состояние
 * контейнера — с учётом активных фильтров, тултипов и изменения визуализации.
 * html2canvas и jsPDF подгружаются лениво, чтобы не увеличивать основной бандл.
 */

const PNG_SCALE = 2;
const PDF_MARGIN = 24;

async function render(node: HTMLElement): Promise<HTMLCanvasElement> {
  const { default: html2canvas } = await import('html2canvas');
  return html2canvas(node, {
    scale: PNG_SCALE,
    backgroundColor: getComputedStyle(node).backgroundColor || '#ffffff',
    useCORS: true,
    logging: false,
    onclone: (document_) => {
      const cloned = document_.querySelector<HTMLElement>('[data-chart-export]');
      if (cloned) {
        resolveCssVariables(cloned);
      }
    },
  });
}

/** CSS-переменные темы не резолвятся html2canvas — подставляем значения явно. */
function resolveCssVariables(root: ParentNode): void {
  const computed = getComputedStyle(document.documentElement);
  const elements: Element[] = [
    ...(root instanceof Element ? [root] : []),
    ...Array.from(root.querySelectorAll('*')),
  ];
  elements.forEach((el) => {
    const style = (el as HTMLElement).style;
    if (style?.cssText?.includes('var(')) {
      for (let i = style.length - 1; i >= 0; i -= 1) {
        const prop = style.item(i);
        const value = style.getPropertyValue(prop);
        if (value.includes('var(')) {
          style.setProperty(prop, substituteVars(value, computed));
        }
      }
    }

    const attrs = el.getAttributeNames();
    for (const attr of attrs) {
      if (!attr.startsWith('fill') && !attr.startsWith('stroke')) {
        continue;
      }
      const value = el.getAttribute(attr);
      if (value?.includes('var(')) {
        el.setAttribute(attr, substituteVars(value, computed));
      }
    }
  });
}

function substituteVars(value: string, computed: CSSStyleDeclaration): string {
  return value.replace(/var\(\s*(--[\w-]+)\s*\)/g, (_, name: string) => {
    const resolved = computed.getPropertyValue(name).trim();
    return resolved || '#888888';
  });
}

function sanitizeFilename(name: string): string {
  return name.replace(/[\\/:*?"<>|]+/g, '-').trim() || 'diagram';
}

export async function exportNodeAsPng(
  node: HTMLElement,
  filename: string
): Promise<void> {
  const canvas = await render(node);
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/png')
  );
  if (!blob) {
    throw new Error('Не удалось сформировать PNG');
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${sanitizeFilename(filename)}.png`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function exportNodeAsPdf(
  node: HTMLElement,
  filename: string,
  title?: string
): Promise<void> {
  const [{ jsPDF }, canvas] = await Promise.all([import('jspdf'), render(node)]);
  const pdf = new jsPDF({
    orientation: canvas.width >= canvas.height ? 'landscape' : 'portrait',
    unit: 'pt',
    format: 'a4',
  });

  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const maxWidth = pageWidth - PDF_MARGIN * 2;
  const maxHeight = pageHeight - PDF_MARGIN * 2;

  const ratio = Math.min(maxWidth / canvas.width, maxHeight / canvas.height);
  const renderWidth = canvas.width * ratio;
  const renderHeight = canvas.height * ratio;
  const offsetX = (pageWidth - renderWidth) / 2;
  const offsetY = title ? PDF_MARGIN + 20 : (pageHeight - renderHeight) / 2;

  if (title) {
    pdf.setFontSize(14);
    pdf.text(title, PDF_MARGIN, PDF_MARGIN + 4);
  }

  pdf.addImage(
    canvas.toDataURL('image/png'),
    'PNG',
    offsetX,
    offsetY,
    renderWidth,
    renderHeight
  );
  pdf.save(`${sanitizeFilename(filename)}.pdf`);
}
