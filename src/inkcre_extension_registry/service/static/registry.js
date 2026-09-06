/* Browser enhancements share the Python Worker's origin and release API. */
const $ = (selector) => document.querySelector(selector)
const announce = (message) => {
  $('#announcement').textContent = message
  clearTimeout(announce.timer)
  announce.timer = setTimeout(() => {
    $('#announcement').textContent = ''
  }, 4500)
}

const themeButton = $('.theme-button')
function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme
  const dark = theme === 'dark' || (!theme && matchMedia('(prefers-color-scheme: dark)').matches)
  themeButton?.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`)
}
try {
  applyTheme(localStorage.getItem('registry-theme'))
} catch {
  applyTheme(null)
}
themeButton?.addEventListener('click', () => {
  const dark =
    document.documentElement.dataset.theme === 'dark' ||
    (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches)
  const theme = dark ? 'light' : 'dark'
  applyTheme(theme)
  try {
    localStorage.setItem('registry-theme', theme)
  } catch {
    /* Theme still works for this page. */
  }
})
document.addEventListener('keydown', (event) => {
  if (
    event.key === '/' &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.target.closest('input, textarea, select, [contenteditable]') &&
    $('#search')
  ) {
    event.preventDefault()
    $('#search').focus()
  }
})
for (const button of document.querySelectorAll('.copy-button')) {
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy)
      announce('Extension ID copied.')
    } catch {
      announce('Couldn’t copy. Select the extension ID above to copy it manually.')
    }
  })
}

if ($('#connect-form')) {
  let credential = ''
  let namespace = ''
  let offset = 0
  let nextOffset = null
  let connection = new AbortController()
  let action = null
  const status = (selector, message, error = false) => {
    const element = $(selector)
    element.textContent = message
    element.classList.toggle('error', error)
  }
  const element = (tag, text, className) => {
    const node = document.createElement(tag)
    if (text) node.textContent = text
    if (className) node.className = className
    return node
  }
  function disconnect() {
    connection.abort()
    connection = new AbortController()
    credential = ''
    namespace = ''
    offset = 0
    nextOffset = null
    action = null
    $('#token').value = ''
    $('#namespace-name').textContent = ''
    $('#release-list').replaceChildren()
    $('#workspace').hidden = true
    $('#connect-panel').hidden = false
    for (const dialog of document.querySelectorAll('dialog')) dialog.close()
  }
  async function api(path, { method = 'GET', body } = {}) {
    const current = connection
    const headers = { Authorization: `Bearer ${credential}` }
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(body)
    }
    let response
    try {
      response = await fetch(path, {
        method,
        headers,
        body,
        cache: 'no-store',
        credentials: 'omit',
        signal: AbortSignal.any([connection.signal, AbortSignal.timeout(60000)]),
      })
    } catch (error) {
      if (error.name === 'AbortError') throw error
      throw new Error(
        'The Registry could not be reached. If you were making a change, refresh to check its state before retrying.',
      )
    }
    const data = await response.json().catch(() => null)
    if (current !== connection || current.signal.aborted) {
      throw new DOMException('Publisher disconnected', 'AbortError')
    }
    if (!response.ok) {
      if (response.status === 401) {
        disconnect()
        status(
          '#connect-status',
          'Your credential wasn’t accepted. Reconnect with a valid publisher credential.',
          true,
        )
      }
      const detail = Array.isArray(data?.detail)
        ? data.detail
            .map((item) => `${item.loc?.slice(1).join(' / ') || 'Release'}: ${item.msg}`)
            .join('; ')
        : data?.detail
      throw new Error(
        typeof detail === 'string'
          ? detail
          : `Request failed (${response.status}). Please refresh and try again.`,
      )
    }
    return data
  }
  function openAction(release, kind) {
    action = { release, kind }
    const descriptions = {
      publish: ['Publish this release?', 'This version will become public.', 'Publish release'],
      yank: [
        'Withdraw this release?',
        'This version will leave the catalog and new discovery. Existing distribution URLs remain available; withdrawal does not uninstall it from anyone’s workspace.',
        'Withdraw release',
      ],
      unyank: [
        'Restore this release?',
        'This version will be available for discovery again.',
        'Restore release',
      ],
      'module-federation': [
        'Upload a Web snapshot',
        'Different bytes require a new version.',
        'Upload snapshot',
      ],
    }
    const [title, description, label] = descriptions[kind]
    $('#action-title').textContent = title
    $('#action-description').textContent = `${release.name} · ${release.version}. ${description}`
    $('#confirm-action').textContent = label
    $('#reason-field').hidden = kind !== 'yank'
    $('#yank-reason').required = kind === 'yank'
    $('#upload-field').hidden = kind !== 'module-federation'
    $('#snapshot').required = kind === 'module-federation'
    $('#action-form').reset()
    status('#action-status', '')
    $('#action-dialog').showModal()
  }
  function renderWorkspace(data) {
    namespace = data.namespace
    offset = data.offset
    nextOffset = data.next_offset
    $('#previous-page').disabled = offset === 0
    $('#next-page').disabled = nextOffset === null
    $('#page-position').textContent = `Page ${Math.floor(offset / 10) + 1}`
    $('#release-pagination').hidden = offset === 0 && nextOffset === null
    $('#namespace-name').textContent = namespace
    $('#release-count').textContent = `${data.releases.length} on this page`
    const list = $('#release-list')
    list.replaceChildren()
    if (!data.releases.length) {
      const empty = element('div', null, 'empty-state')
      empty.append(element('p', 'No releases.'))
      list.append(empty)
    }
    for (const release of data.releases) {
      const row = element('article', null, 'release-row')
      const info = element('div')
      info.append(
        element('h3', release.nickname),
        element('p', `${release.name} · ${release.version}`),
      )
      const state = {
        preparing: 'Preparing',
        published: 'Published',
        yanked: 'Withdrawn',
        blocked: 'Blocked by operator',
      }[release.state]
      info.append(element('span', state, 'badge'))
      const distributions = [release.python && 'Python', release.module_federation && 'Web']
        .filter(Boolean)
        .join(' + ')
      const uploaded = [
        release.python_uploaded && 'Python uploaded',
        release.web_uploaded && 'Web uploaded',
      ]
        .filter(Boolean)
        .join(' · ')
      info.append(element('p', uploaded || `${distributions} declared · awaiting upload`))
      const actions = element('div', null, 'release-actions')
      const button = (label, kind) => {
        const node = element('button', label, 'button')
        node.type = 'button'
        node.addEventListener('click', () => openAction(release, kind))
        actions.append(node)
        return node
      }
      if (release.state === 'preparing') {
        if (release.module_federation) button('Upload Web ZIP', 'module-federation')
        const publish = button('Publish', 'publish')
        publish.disabled = !release.python_uploaded && !release.web_uploaded
        if (publish.disabled) publish.title = 'Upload a distribution before publishing'
      }
      if (release.state === 'published') {
        const link = element('a', 'View release ↗', 'button')
        link.href = `/explore/${release.name}?version=${encodeURIComponent(release.version)}`
        actions.append(link)
        button('Withdraw', 'yank')
      }
      if (release.state === 'yanked') button('Restore', 'unyank')
      row.append(info, actions)
      list.append(row)
    }
    $('#connect-panel').hidden = true
    $('#workspace').hidden = false
  }
  async function refresh(pageOffset = offset) {
    const current = connection
    const data = await api(`/v1/publisher?offset=${pageOffset}`)
    if (current !== connection || current.signal.aborted) return
    renderWorkspace(data)
  }
  async function submit(form, statusSelector, work) {
    const button = form.querySelector('[type="submit"]')
    const dialog = form.closest('dialog')
    const close = dialog?.querySelector('.close-dialog')
    const original = button.textContent
    button.disabled = true
    button.textContent = 'Working…'
    if (close) close.disabled = true
    form.setAttribute('aria-busy', 'true')
    status(statusSelector, '')
    try {
      await work()
    } catch (error) {
      if (error.name !== 'AbortError') status(statusSelector, error.message, true)
    } finally {
      button.disabled = false
      button.textContent = original
      if (close) close.disabled = false
      form.removeAttribute('aria-busy')
    }
  }
  $('#connect-form').addEventListener('submit', (event) => {
    event.preventDefault()
    submit(event.currentTarget, '#connect-status', async () => {
      credential = $('#token').value.trim()
      await refresh()
      $('#token').value = ''
      if (namespace) {
        $('#new-release').focus()
        announce('Publisher workspace connected.')
      }
    })
  })
  $('#disconnect').addEventListener('click', () => {
    disconnect()
    status('#connect-status', 'Disconnected. Credential cleared.')
    $('#token').focus()
  })
  window.addEventListener('pagehide', disconnect)
  $('#refresh').addEventListener('click', async (event) => {
    event.currentTarget.disabled = true
    status('#workspace-status', 'Refreshing…')
    try {
      await refresh()
      status('#workspace-status', 'Up to date.')
    } catch (error) {
      if (error.name !== 'AbortError') status('#workspace-status', error.message, true)
    } finally {
      $('#refresh').disabled = false
    }
  })
  for (const [selector, direction] of [
    ['#previous-page', -1],
    ['#next-page', 1],
  ]) {
    $(selector).addEventListener('click', async () => {
      const target = direction < 0 ? Math.max(0, offset - 10) : nextOffset
      if (target === null) return
      $('#previous-page').disabled = true
      $('#next-page').disabled = true
      status('#workspace-status', 'Loading releases…')
      try {
        await refresh(target)
        status('#workspace-status', '')
      } catch (error) {
        if (error.name !== 'AbortError') status('#workspace-status', error.message, true)
      } finally {
        $('#previous-page').disabled = offset === 0
        $('#next-page').disabled = nextOffset === null
      }
    })
  }
  $('#new-release').addEventListener('click', () => {
    $('#release-form').reset()
    status('#release-status', '')
    $('#release-dialog').showModal()
  })
  for (const dialog of document.querySelectorAll('dialog')) {
    dialog.querySelector('.close-dialog').addEventListener('click', () => dialog.close())
    dialog.addEventListener('cancel', (event) => {
      if (dialog.querySelector('[aria-busy="true"]')) event.preventDefault()
    })
  }
  async function updateAfterChange(message, pageOffset = offset) {
    status('#workspace-status', message)
    try {
      await refresh(pageOffset)
    } catch (error) {
      if (error.name !== 'AbortError')
        status(
          '#workspace-status',
          `${message} Couldn’t refresh the list. Use Refresh to check its current state.`,
          true,
        )
    }
  }
  $('#release-form').addEventListener('submit', (event) => {
    event.preventDefault()
    const form = event.currentTarget
    submit(form, '#release-status', async () => {
      const fields = new FormData(form)
      const value = (key) => fields.get(key).trim()
      await api(`/v1/extensions/${namespace}/${encodeURIComponent(value('slug'))}/releases`, {
        method: 'POST',
        body: {
          nickname: value('nickname'),
          version: value('version'),
          module_federation: {
            host_sdk: '@inkcre/core',
            host_sdk_version: value('host_range'),
            source_repository: value('repository'),
            source_revision: value('revision'),
          },
        },
      })
      $('#release-dialog').close()
      await updateAfterChange('Release prepared.', 0)
    })
  })
  $('#action-form').addEventListener('submit', (event) => {
    event.preventDefault()
    const { release, kind } = action
    submit(event.currentTarget, '#action-status', async () => {
      let body
      if (kind === 'yank') body = { reason: $('#yank-reason').value.trim() }
      if (kind === 'module-federation') {
        const file = $('#snapshot').files[0]
        if (!file || file.size > 20 * 1024 * 1024 - 4096)
          throw new Error('Choose a ZIP smaller than 20 MiB, including upload overhead.')
        body = new FormData()
        body.append('content', file)
      }
      await api(
        `/v1/extensions/${release.name}/releases/${encodeURIComponent(release.version)}/${kind}`,
        { method: 'POST', body },
      )
      $('#action-dialog').close()
      const messages = {
        publish: 'Release published. It’s now in the catalog.',
        yank: 'Release withdrawn from discovery.',
        unyank: 'Release restored to the catalog.',
        'module-federation': 'Snapshot uploaded. Your release is ready to publish.',
      }
      await updateAfterChange(messages[kind])
    })
  })
}
