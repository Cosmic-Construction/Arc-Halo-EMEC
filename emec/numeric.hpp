#pragma once

// Small array helpers for the header-only EMEC simulator.
// Names match the quantities used by the induction-machine model
// (phase vectors, inductance matrices) rather than a generic tensor API.

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <initializer_list>
#include <stdexcept>
#include <vector>

namespace emec {

inline constexpr double kPi = 3.14159265358979323846;

inline double positive_mod(double value, double modulus) {
    if (modulus == 0.0) {
        return 0.0;
    }
    double wrapped = std::fmod(value, modulus);
    if (wrapped < 0.0) {
        wrapped += modulus;
    }
    return wrapped;
}

inline double clip(double value, double lo, double hi) {
    return std::min(hi, std::max(lo, value));
}

class Vec {
public:
    Vec() = default;
    explicit Vec(std::size_t n, double fill = 0.0) : data_(n, fill) {}
    Vec(std::initializer_list<double> values) : data_(values) {}

    std::size_t size() const { return data_.size(); }
    bool empty() const { return data_.empty(); }
    double* data() { return data_.data(); }
    const double* data() const { return data_.data(); }

    double& operator[](std::size_t i) { return data_.at(i); }
    double operator[](std::size_t i) const { return data_.at(i); }

    std::vector<double>::iterator begin() { return data_.begin(); }
    std::vector<double>::iterator end() { return data_.end(); }
    std::vector<double>::const_iterator begin() const { return data_.begin(); }
    std::vector<double>::const_iterator end() const { return data_.end(); }

    Vec copy() const { return *this; }

    double sum() const {
        double total = 0.0;
        for (double v : data_) {
            total += v;
        }
        return total;
    }

    double mean() const {
        if (data_.empty()) {
            return 0.0;
        }
        return sum() / static_cast<double>(data_.size());
    }

    double max_abs() const {
        double peak = 0.0;
        for (double v : data_) {
            peak = std::max(peak, std::abs(v));
        }
        return peak;
    }

private:
    std::vector<double> data_;
};

inline Vec operator+(const Vec& a, const Vec& b) {
    if (a.size() != b.size()) {
        throw std::invalid_argument("phase vector size mismatch");
    }
    Vec out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] + b[i];
    }
    return out;
}

inline Vec operator-(const Vec& a, const Vec& b) {
    if (a.size() != b.size()) {
        throw std::invalid_argument("phase vector size mismatch");
    }
    Vec out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] - b[i];
    }
    return out;
}

inline Vec operator*(const Vec& a, double scale) {
    Vec out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] * scale;
    }
    return out;
}

inline Vec operator*(double scale, const Vec& a) { return a * scale; }

inline Vec operator/(const Vec& a, double scale) {
    Vec out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] / scale;
    }
    return out;
}

inline Vec operator*(const Vec& a, const Vec& b) {
    if (a.size() != b.size()) {
        throw std::invalid_argument("phase vector size mismatch");
    }
    Vec out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] * b[i];
    }
    return out;
}

inline Vec clip(const Vec& value, double lo, double hi) {
    Vec out(value.size());
    for (std::size_t i = 0; i < value.size(); ++i) {
        out[i] = clip(value[i], lo, hi);
    }
    return out;
}

inline Vec zeros_like(const Vec& value) { return Vec(value.size(), 0.0); }

// Row-major inductance / geometry matrix.
class Mat {
public:
    Mat() = default;
    Mat(std::size_t rows, std::size_t cols, double fill = 0.0)
        : rows_(rows), cols_(cols), data_(rows * cols, fill) {}

    std::size_t rows() const { return rows_; }
    std::size_t cols() const { return cols_; }

    double& operator()(std::size_t r, std::size_t c) { return data_.at(r * cols_ + c); }
    double operator()(std::size_t r, std::size_t c) const { return data_.at(r * cols_ + c); }

    static Mat identity(std::size_t n) {
        Mat eye(n, n, 0.0);
        for (std::size_t i = 0; i < n; ++i) {
            eye(i, i) = 1.0;
        }
        return eye;
    }

    static Mat zeros(std::size_t rows, std::size_t cols) { return Mat(rows, cols, 0.0); }

    Mat transpose() const {
        Mat out(cols_, rows_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t c = 0; c < cols_; ++c) {
                out(c, r) = (*this)(r, c);
            }
        }
        return out;
    }

    Vec multiply(const Vec& vector) const {
        if (vector.size() != cols_) {
            throw std::invalid_argument("inductance matrix / current size mismatch");
        }
        Vec out(rows_, 0.0);
        for (std::size_t r = 0; r < rows_; ++r) {
            double sum = 0.0;
            for (std::size_t c = 0; c < cols_; ++c) {
                sum += (*this)(r, c) * vector[c];
            }
            out[r] = sum;
        }
        return out;
    }

private:
    std::size_t rows_ = 0;
    std::size_t cols_ = 0;
    std::vector<double> data_;
};

inline Vec operator*(const Mat& matrix, const Vec& vector) { return matrix.multiply(vector); }

struct FluxLinkages {
    Vec stator;
    Vec rotor;
};

}  // namespace emec
