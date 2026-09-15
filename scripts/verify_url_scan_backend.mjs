// Exercise the actual backend controllers and AI bridge with no .env reads,
// database connections or external network requests.
import assert from 'node:assert/strict'

process.env.DOTENV_CONFIG_PATH = 'D:/BanteayDigital-AI/.backend-url-implementation/nonexistent-test-config'
process.env.VIRUSTOTAL_API_KEY = 'verification-only-not-a-real-key'
process.env.AI_SERVICE_URL = 'http://127.0.0.1:8000'
process.env.AI_SERVICE_API_KEY = 'verification-only-ai-key'

let providerCalls = 0
let aiCalls = 0
globalThis.fetch = async (address, options) => {
  if (String(address).startsWith('https://www.virustotal.com/api/v3/urls/')) {
    providerCalls++
    assert.equal(options.headers['x-apikey'], process.env.VIRUSTOTAL_API_KEY)
    return Response.json({ data: { type: 'url', attributes: {
      last_analysis_date: Math.floor(Date.now() / 1000),
      last_analysis_stats: { malicious: 2, suspicious: 0, harmless: 60, undetected: 10, timeout: 0 },
      last_analysis_results: { Engine: { category: 'malicious', result: 'phishing' } },
    } } })
  }
  assert.equal(String(address), 'http://127.0.0.1:8000/api/v1/analyze')
  aiCalls++
  assert.equal(options.headers['X-AI-Service-Key'], process.env.AI_SERVICE_API_KEY)
  const body = JSON.parse(options.body)
  assert.equal(body.type, 'URL')
  assert.equal(body.urlEvidence.stats.malicious, 2)
  assert.equal(body.urlEvidence.detections[0].result, 'phishing')
  return Response.json({ assessment: 'NO_STRONG_WARNING_SIGNS', summary: 'No warning signs.', recommendedActions: ['Proceed carefully.'] })
}

const { create, getById } = await import('file:///D:/BanteayDigital/Backend/src/controllers/url-scan.controller.js')
const { urlScans } = await import('file:///D:/BanteayDigital/Backend/src/services/url-scan.runtime.js')
const { createUrlScanSchema, urlScanIdSchema } = await import('file:///D:/BanteayDigital/Backend/src/validators/url-scan.validator.js')
const { default: env } = await import('file:///D:/BanteayDigital/Backend/src/config/env.js')

function response() {
  return { headers: {}, statusCode: 200,
    set(key, value) { this.headers[key] = value; return this },
    status(code) { this.statusCode = code; return this },
    json(body) { this.body = body; return this },
  }
}
const fail = error => { throw error }
assert.equal(createUrlScanSchema.safeParse({ url: 'https://example.com' }).success, true)
assert.equal(createUrlScanSchema.safeParse({ url: 'http://127.0.0.1' }).success, false)
assert.equal(createUrlScanSchema.safeParse({ url: 'https://example.com/?token=private' }).success, false)
assert.equal(urlScanIdSchema.safeParse({ id: 'invalid' }).success, false)
const accepted = response()
await create({ auth: { userId: 'u1' }, body: { url: 'https://example.com' } }, accepted, fail)
assert.equal(accepted.statusCode, 202)
const id = accepted.body.scan.id
assert.equal(accepted.headers.Location, `/api/v1/scans/url/${id}`)
await urlScans.wait(id)
const result = response()
await getById({ auth: { userId: 'u1' }, params: { id } }, result, fail)
assert.equal(result.body.scan.status, 'COMPLETED')
assert.equal(result.body.scan.result.riskLevel, 'HIGH')
assert.equal(result.body.scan.result.explanationSource, 'RULES')
assert.equal(result.headers['Cache-Control'], 'no-store')
let error
await getById({ auth: { userId: 'u2' }, params: { id } }, response(), value => { error = value })
assert.equal(error.statusCode, 404)
env.virusTotalApiKey = undefined
await create({ auth: { userId: 'u1' }, body: { url: 'https://example.com' } }, response(), value => { error = value })
assert.equal(error.statusCode, 503)
assert.equal(providerCalls, 1)
assert.equal(aiCalls, 1)
console.log('Backend controllers, validators, provider-to-AI forwarding, risk floor and owner isolation passed (all network calls mocked).')
