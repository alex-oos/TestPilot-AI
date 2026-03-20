import request from '../utils/request'

export async function loginByFallback(username: string, password: string) {
  const postByBase = () => request.post('/login', {
    username,
    password,
  })

  try {
    return await postByBase()
    // return await postByBase(DIRECT_BACKEND_API_BASE)
  } catch (directError: any) {
    try {
      return await postByBase()
      // return await postByBase(API_BASE_URL)
    } catch (proxyError: any) {
      throw proxyError?.response ? proxyError : directError
    }
  }
}
