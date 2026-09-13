import path from 'node:path'
import { readdir, readFile, rm } from 'node:fs/promises'

import EleventyVitePlugin from '@11ty/eleventy-plugin-vite'

function carryEleventyOutput() {
  const carried = new Map()
  let root

  return {
    name: 'saggre:carry-eleventy-output',
    enforce: 'pre',
    apply: 'build',

    configResolved(config) {
      root = config.root
    },

    async buildStart() {
      for (const entry of await readdir(root, { withFileTypes: true })) {
        if (!entry.isFile() || entry.name.endsWith('.html')) continue
        const file = path.join(root, entry.name)
        carried.set(entry.name, await readFile(file))
        await rm(file)
      }
    },

    generateBundle() {
      for (const [fileName, source] of carried) {
        this.emitFile({ type: 'asset', fileName, source })
      }
    },
  }
}

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(EleventyVitePlugin, {
    viteOptions: {
      plugins: [carryEleventyOutput()],
      resolve: {
        alias: { '/src': path.resolve('src') },
      },
      css: {
        lightningcss: {
          errorRecovery: true,
        },
      },
      build: {
        assetsDir: 'assets/build',
        modulePreload: { polyfill: false },
        rolldownOptions: {
          output: {
            assetFileNames: (asset) =>
              (asset.names?.[0] ?? '').endsWith('.css')
                ? 'assets/build/main-[hash][extname]'
                : 'assets/build/[name]-[hash][extname]',
          },
        },
      },
    },
  })

  // RSS 2.0 wants RFC 822 dates; a date with no time of day is midnight UTC.
  eleventyConfig.addFilter('rfc822', (iso) => new Date(`${iso}T00:00:00Z`).toUTCString())

  return {
    dir: {
      input: 'src/pages',
      includes: '../_includes',
      data: '../_data',
      output: 'dist',
    },
    htmlTemplateEngine: 'njk',
  }
}
