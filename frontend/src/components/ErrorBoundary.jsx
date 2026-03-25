import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <p className="font-medium">Något gick fel med den här komponenten.</p>
          <button onClick={() => this.setState({ hasError: false })}
            className="mt-2 text-red-600 underline text-xs">
            Försök igen
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
