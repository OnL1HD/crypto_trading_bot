const UTC_MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface FormatUtcTimestampOptions {
  includeDate?: boolean
  includeTime?: boolean
  includeSeconds?: boolean
  includeTimezone?: boolean
}

function pad2(value: number): string {
  return value.toString().padStart(2, '0')
}

function parseDate(value: string | number | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatUtcTimestamp(
  value: string | number | Date | null | undefined,
  options: FormatUtcTimestampOptions = {},
): string {
  const date = parseDate(value)
  if (!date) {
    return '--'
  }

  const {
    includeDate = true,
    includeTime = true,
    includeSeconds = false,
    includeTimezone = true,
  } = options

  const year = date.getUTCFullYear()
  const month = pad2(date.getUTCMonth() + 1)
  const day = pad2(date.getUTCDate())
  const hours = pad2(date.getUTCHours())
  const minutes = pad2(date.getUTCMinutes())
  const seconds = pad2(date.getUTCSeconds())

  const datePart = `${year}-${month}-${day}`
  const timePart = includeSeconds ? `${hours}:${minutes}:${seconds}` : `${hours}:${minutes}`
  const timezonePart = includeTimezone ? ' UTC' : ''

  if (includeDate && includeTime) {
    return `${datePart} ${timePart}${timezonePart}`
  }

  if (includeDate) {
    return datePart
  }

  if (includeTime) {
    return `${timePart}${timezonePart}`
  }

  return datePart
}

export function formatUtcMonthDayTime(value: string | number | Date | null | undefined, includeMinutes = true): string {
  const date = parseDate(value)
  if (!date) {
    return '--'
  }

  const month = UTC_MONTHS_SHORT[date.getUTCMonth()]
  const day = pad2(date.getUTCDate())
  const hours = pad2(date.getUTCHours())
  const minutes = pad2(date.getUTCMinutes())

  return includeMinutes ? `${month} ${day} ${hours}:${minutes}` : `${month} ${day} ${hours}`
}

export function formatUtcTime(value: string | number | Date | null | undefined): string {
  const date = parseDate(value)
  if (!date) {
    return '--'
  }

  return `${pad2(date.getUTCHours())}:${pad2(date.getUTCMinutes())}`
}
