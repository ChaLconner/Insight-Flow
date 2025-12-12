import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl

    // Check if we're on the root path
    if (pathname === '/') {
        // Check for auth cookie/token (simplified check)
        // Note: In a real app, you'd verification the token
        // For now, we'll rely on the client to handle invalid tokens
        // but the presence of the cookie allows us to skip the login page
        const hasAuth = request.cookies.has('auth-storage') || request.cookies.has('token')

        if (hasAuth) {
            return NextResponse.redirect(new URL('/dashboard', request.url))
        } else {
            return NextResponse.redirect(new URL('/auth/login', request.url))
        }
    }

    return NextResponse.next()
}

export const config = {
    matcher: '/',
}
