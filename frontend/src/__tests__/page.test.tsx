import { render, screen } from '@testing-library/react'
import Home from '@/app/page'

describe('Home', () => {
  it('renders FlatWatch heading', () => {
    render(<Home />)
    const heading = screen.getByText('FlatWatch')
    expect(heading).toBeInTheDocument()
  })

  it('renders tagline', () => {
    render(<Home />)
    const tagline = screen.getByText('Society Cash Tracker')
    expect(tagline).toBeInTheDocument()
  })

  it('renders Get Started link', () => {
    render(<Home />)
    const link = screen.getByRole('link', { name: 'Get Started' })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/dashboard')
  })

  it('renders system status', () => {
    render(<Home />)
    const status = screen.getByText('System initializing...')
    expect(status).toBeInTheDocument()
  })
})
