// Підготовка файлів лікарняного перед завантаженням.
// Великі фото стискаються до ~2400 px по довшій стороні (текст лишається чітким),
// PDF і формати, які браузер не вміє декодувати (напр. HEIC на Android), ідуть як є —
// сервер їх прийме.

export const ACCEPT = 'application/pdf,image/*'
export const MAX_FILE_BYTES = 10 * 1024 * 1024
export const MAX_FILES_PER_UPLOAD = 5

const MAX_SIDE = 2400
const COMPRESS_FROM_BYTES = 1.5 * 1024 * 1024
const SKIP_TYPES = new Set(['image/gif', 'image/svg+xml'])

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => resolve({ img, url })
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('decode'))
    }
    img.src = url
  })
}

export async function prepareFile(file) {
  if (!file.type.startsWith('image/') || SKIP_TYPES.has(file.type) || file.size < COMPRESS_FROM_BYTES) {
    return file
  }
  try {
    const { img, url } = await loadImage(file)
    const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(img.naturalWidth * scale)
    canvas.height = Math.round(img.naturalHeight * scale)
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    URL.revokeObjectURL(url)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
    if (!blob || blob.size >= file.size) return file
    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() })
  } catch {
    return file
  }
}

export function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const isImage = (file) => file.type.startsWith('image/')
