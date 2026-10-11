// Whole numbers of any size, and exact fractions.
//
// A whole number is a `Number` while it is a safe integer and a `BigInt` otherwise, so the
// same value always has the same form. A fraction is `{n, d}`, two `BigInt`s in lowest
// terms with `d` above 0.

const LARGEST = BigInt(Number.MAX_SAFE_INTEGER);

// The whole number of a `Number` that is an integer or of a `BigInt`, in its one form.
export function whole(value) {
  if (typeof value === "bigint") {
    return value >= -LARGEST && value <= LARGEST ? Number(value) : value;
  }
  if (!Number.isSafeInteger(value)) {
    throw new RangeError(`${value} is not a whole number`);
  }
  return value === 0 ? 0 : value;
}

// The whole number that a text of decimal digits, with or without a minus sign, spells.
export function fromDigits(text) {
  return text.length <= 15 ? whole(Number(text)) : whole(BigInt(text));
}

// The sum of two whole numbers.
export function plus(a, b) {
  if (typeof a === "number" && typeof b === "number") {
    const sum = a + b;
    if (Number.isSafeInteger(sum)) {
      return sum;
    }
  }
  return whole(BigInt(a) + BigInt(b));
}

// The product of two whole numbers.
export function times(a, b) {
  if (typeof a === "number" && typeof b === "number") {
    const product = a * b;
    if (Number.isSafeInteger(product)) {
      return product === 0 ? 0 : product;
    }
  }
  return whole(BigInt(a) * BigInt(b));
}

// a divided by b for two `BigInt`s, rounded toward minus infinity. The division of
// `BigInt` itself rounds toward zero.
export function floorDiv(a, b) {
  const quotient = a / b;
  return a % b !== 0n && (a < 0n) !== (b < 0n) ? quotient - 1n : quotient;
}

function gcd(a, b) {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y !== 0n) {
    [x, y] = [y, x % y];
  }
  return x;
}

function isFraction(value) {
  return value !== null && typeof value === "object" && typeof value.n === "bigint" && typeof value.d === "bigint";
}

function integer(value) {
  if (typeof value === "bigint") {
    return value;
  }
  if (!Number.isSafeInteger(value)) {
    throw new RangeError(`${value} is not a whole number`);
  }
  return BigInt(value);
}

// The fraction n / d in lowest terms. `n` and `d` are whole numbers; `n` may also be a
// fraction, which is then divided by `d`.
export function fraction(n, d = 1) {
  if (isFraction(n)) {
    return d === 1 ? n : div(n, fraction(d));
  }
  let top = integer(n);
  let bottom = integer(d);
  if (bottom === 0n) {
    throw new RangeError("a fraction has no denominator of 0");
  }
  if (bottom < 0n) {
    top = -top;
    bottom = -bottom;
  }
  const common = gcd(top, bottom);
  return common === 1n ? {n: top, d: bottom} : {n: top / common, d: bottom / common};
}

export function add(a, b) {
  const x = fraction(a);
  const y = fraction(b);
  return fraction(x.n * y.d + y.n * x.d, x.d * y.d);
}

export function sub(a, b) {
  const x = fraction(a);
  const y = fraction(b);
  return fraction(x.n * y.d - y.n * x.d, x.d * y.d);
}

export function mul(a, b) {
  const x = fraction(a);
  const y = fraction(b);
  return fraction(x.n * y.n, x.d * y.d);
}

export function div(a, b) {
  const x = fraction(a);
  const y = fraction(b);
  return fraction(x.n * y.d, x.d * y.n);
}

// -1, 0 or 1 as a is below, equal to or above b.
export function compare(a, b) {
  const x = fraction(a);
  const y = fraction(b);
  const left = x.n * y.d;
  const right = y.n * x.d;
  return left < right ? -1 : left > right ? 1 : 0;
}

// The largest whole number that is not above the fraction, as a `BigInt`.
export function floor(a) {
  const x = fraction(a);
  return floorDiv(x.n, x.d);
}

// The smallest whole number that is not below the fraction, as a `BigInt`.
export function ceil(a) {
  const x = fraction(a);
  return -floorDiv(-x.n, x.d);
}

// Whether the fraction is a whole number.
export function isWhole(a) {
  return fraction(a).d === 1n;
}

// The fraction rounded to the nearest whole number, halves away from zero, as a `BigInt`.
export function rounded(a) {
  const x = fraction(a);
  const magnitude = x.n < 0n ? -x.n : x.n;
  const nearest = (2n * magnitude + x.d) / (2n * x.d);
  return x.n < 0n ? -nearest : nearest;
}

const DECIMAL = /^([+-]?)([0-9]*)(?:\.([0-9]*))?(?:[eE]([+-]?[0-9]+))?$/;

// The number a decimal text spells, times `scale`, as a fraction: an optional sign, digits
// with an optional fraction, and an optional exponent. It is computed on the digits.
export function fromDecimal(text, scale = 1) {
  const match = DECIMAL.exec(text);
  if (match === null || (match[2] === "" && (match[3] === undefined || match[3] === ""))) {
    throw new RangeError(`"${text}" is not a decimal number`);
  }
  const digits = match[2] + (match[3] === undefined ? "" : match[3]);
  const exponent = (match[4] === undefined ? 0 : Number(match[4])) - (match[3] === undefined ? 0 : match[3].length);
  let n = BigInt(digits) * integer(scale);
  let d = 1n;
  if (exponent >= 0) {
    n *= 10n ** BigInt(exponent);
  } else {
    d = 10n ** BigInt(-exponent);
  }
  return fraction(match[1] === "-" ? -n : n, d);
}

function bits(value) {
  return value.toString(2).length;
}

// The `Number` nearest to a fraction that is not negative, halves to the even one, as the
// division of two floating-point numbers gives it when both are exact.
function nearestNumber(x) {
  if (x.n <= LARGEST && x.d <= LARGEST) {
    return Number(x.n) / Number(x.d);
  }
  // 55 bits of quotient or more: 53 for the number, and at least two to round with.
  const shift = 55 - (bits(x.n) - bits(x.d));
  const top = shift > 0 ? x.n << BigInt(shift) : x.n;
  const bottom = shift < 0 ? x.d << BigInt(-shift) : x.d;
  let quotient = top / bottom;
  const exact = top % bottom === 0n;
  const extra = bits(quotient) - 53;
  const dropped = quotient & ((1n << BigInt(extra)) - 1n);
  const half = 1n << BigInt(extra - 1);
  quotient >>= BigInt(extra);
  if (dropped > half || (dropped === half && (!exact || (quotient & 1n) === 1n))) {
    quotient += 1n;
  }
  return Number(quotient) * 2 ** (extra - shift);
}

// A fraction as Python's `format(float(x), ".6g")` writes it: six significant digits of the
// floating-point number nearest to the fraction, halves to the even digit, without zeros at
// the end, and with an exponent of at least two digits when it is below -4 or at least 6.
export function sixDigits(value) {
  const given = fraction(value);
  const negative = given.n < 0n;
  const number = nearestNumber(negative ? {n: -given.n, d: given.d} : given);
  if (number === 0) {
    return "0";
  }
  // The floating-point number as the exact fraction n / d it is.
  let d = 1n;
  let scaled = number;
  while (!Number.isInteger(scaled)) {
    scaled *= 2;
    d *= 2n;
  }
  const n = BigInt(scaled);

  let exponent = Math.floor(Math.log10(number));
  const power = (e) => (e >= 0 ? [10n ** BigInt(e), 1n] : [1n, 10n ** BigInt(-e)]);
  const atLeast = (e) => {
    const [up, down] = power(e);
    return n * down >= d * up;
  };
  while (atLeast(exponent + 1)) {
    exponent += 1;
  }
  while (!atLeast(exponent)) {
    exponent -= 1;
  }

  const [up, down] = power(5 - exponent);
  const top = n * up;
  const bottom = d * down;
  let digits = top / bottom;
  const twice = 2n * (top % bottom);
  if (twice > bottom || (twice === bottom && (digits & 1n) === 1n)) {
    digits += 1n;
  }
  if (digits === 1000000n) {
    digits = 100000n;
    exponent += 1;
  }
  const text = digits.toString();
  const trimmed = (written) => (written.includes(".") ? written.replace(/0+$/, "").replace(/\.$/, "") : written);
  const sign = negative ? "-" : "";
  if (exponent < -4 || exponent >= 6) {
    const size = Math.abs(exponent);
    return `${sign}${trimmed(`${text[0]}.${text.slice(1)}`)}e${exponent < 0 ? "-" : "+"}${size < 10 ? "0" : ""}${size}`;
  }
  if (exponent >= 0) {
    return sign + trimmed(`${text.slice(0, exponent + 1)}.${text.slice(exponent + 1)}`);
  }
  return sign + trimmed(`0.${"0".repeat(-exponent - 1)}${text}`);
}
