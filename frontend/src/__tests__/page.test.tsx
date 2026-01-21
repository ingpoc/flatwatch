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

  it('renders Get Started button', () => {
    render(<Home />)
    const button = screen.getByRole('button', { name: 'Get Started' })
    expect(button).toBeInTheDocument()
  })

  it('renders system status', () => {
    render(<Home />)
    const status = screen.getByText('System initializing...')
    expect(status).toBeInTheDocument()
  })
})
