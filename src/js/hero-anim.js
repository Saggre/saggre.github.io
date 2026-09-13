/**
 * Upgrades the hero still to its animation once the animation has arrived.
 *
 * The page ships a small still and fetches the much larger animation afterwards,
 * so the art above the fold costs nothing at first paint. Without scripting, or
 * when the visitor asks for less motion, the still is what stays.
 */

const HERO_ART = '.vx-hero__art[data-anim]'

/**
 * @returns {boolean} Whether the visitor asked for less motion.
 */
const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true

/**
 * @param {Element} still
 * @returns {{animated: string, fallback: string} | null} Both animation URLs, or
 *   null when either is missing.
 */
const readSources = (still) => {
  const animated = still.getAttribute('data-anim')
  const fallback = still.getAttribute('data-anim-fallback')
  return animated && fallback ? { animated, fallback } : null
}

/**
 * Copies the authored dimensions, not the laid-out ones: `.width` and `.height`
 * report the rendered size, which depends on the viewport at the moment of the
 * swap and would give the replacement a wrong intrinsic ratio.
 *
 * @param {Element} from
 * @param {Element} to
 */
const copyIntrinsicSize = (from, to) => {
  for (const dimension of ['width', 'height']) {
    const value = from.getAttribute(dimension)
    if (value !== null) to.setAttribute(dimension, value)
  }
}

/**
 * Builds the replacement, leaving the format choice to the browser: a real
 * <picture> negotiates its sources exactly as one written in the markup would.
 *
 * @param {Element} still The image to match in presentation.
 * @param {{animated: string, fallback: string}} sources
 * @returns {{picture: HTMLPictureElement, image: HTMLImageElement}}
 */
const buildPicture = (still, sources) => {
  const source = document.createElement('source')
  source.type = 'image/webp'
  source.srcset = sources.animated

  const image = document.createElement('img')
  image.className = still.className
  image.alt = still.alt
  image.decoding = 'async'
  copyIntrinsicSize(still, image)

  const picture = document.createElement('picture')
  picture.append(source, image)
  return { picture, image }
}

/** @param {HTMLElement} element */
const hide = (element) => element.style.setProperty('display', 'none')

/** @param {HTMLElement} element */
const show = (element) => element.style.removeProperty('display')

/**
 * Starts the fetch. The src is the fallback because the WebP <source> above it
 * wins wherever that format is understood, so only older browsers load this one.
 *
 * A detached <picture> is not reliably negotiated, so the element must already
 * be in the document by the time the source is chosen.
 *
 * @param {HTMLImageElement} image
 * @param {string} fallback
 * @returns {Promise<void>} Settles when the animation is ready, or fails to load.
 */
const load = (image, fallback) =>
  new Promise((resolve, reject) => {
    image.addEventListener('load', () => resolve(), { once: true })
    image.addEventListener('error', reject, { once: true })
    image.src = fallback
  })

/**
 * @param {Element} still
 * @param {HTMLElement} picture
 */
const revealInPlaceOf = (still, picture) => {
  show(picture)
  still.remove()
}

/**
 * Swaps the hero still for its animation, or leaves the page as it is.
 */
const upgradeHeroArt = () => {
  const still = document.querySelector(HERO_ART)
  if (!still || prefersReducedMotion()) return

  const sources = readSources(still)
  if (!sources) return

  const { picture, image } = buildPicture(still, sources)
  hide(picture)
  still.after(picture)

  load(image, sources.fallback).then(
    () => revealInPlaceOf(still, picture),
    () => picture.remove(),
  )
}

upgradeHeroArt()
