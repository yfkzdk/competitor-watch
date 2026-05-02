/**
 * useApi — shared fetch composable with loading/error state.
 * Usage: const { data, loading, error, fetch } = useApi()
 */
const useApi = () => {
    const data = Vue.ref(null)
    const loading = Vue.ref(false)
    const error = Vue.ref('')

    const fetch = async (url, options = {}) => {
        loading.value = true
        error.value = ''
        try {
            const resp = await window.fetch(url, options)
            const json = await resp.json()
            if (!resp.ok) throw new Error(json.detail || `HTTP ${resp.status}`)
            data.value = json
            return json
        } catch (err) {
            error.value = err.message
            data.value = null
            return null
        } finally {
            loading.value = false
        }
    }

    return { data, loading, error, fetch }
}
