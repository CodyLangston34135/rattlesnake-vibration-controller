# Rattlesnake Vibration Controller

## Abstract

Rattlesnake is a combined-environments, multiple input/multiple output control system for dynamic excitation of structures under test.  It provides capabilities to control multiple responses on the part using multiple exciters using various control strategies.  Rattlesnake is written in the Python programming language to facilitate multiple input/multiple output vibration research by allowing users to prescribe custom control laws to the controller.  Rattlesnake can target multiple hardware devices, or even perform synthetic control to simulate a test virtually.  Rattlesnake has been used to execute control problems with up to 200 response channels and 24 shaker drives.  This document describes the functionality, architecture, and usage of the Rattlesnake controller to perform combined environments testing.

## Nomenclature

abbreviation | description
--- | ---
6DoF | six degree-of-freedom
API | application programming interface
APSD | auto-power spectral density
CCLD | constant current line drive
COLA | constant overlap and add
CPSD | cross-power spectral density
FEM | finite element model
FFT | fast Fourier transform
FRF | frequency response function
GUI | graphical user interface
ICP | integrated circuit piezoelectric
IDE | integrated development environment
IEPE | integrated electronics piezoelectric
IFFT | inverse fast Fourier transform
JSON | javascript object notation
MIMO | multiple input/multiple output
ReST | representational state transfer
RMS | root-mean-square
SVD | singular value decomposition
TRAC | time response assurance criterion
UI | user interface

## Notation

### Accents

* $\mathbf{x}$ (bold, non-italic typeface) Matrix or vector
* $x$ (non-bold, italic typeface) Scalar or array

### Variables

* $n_f$ Number of frequency lines
* $n_c$ Number of control channels
* $n_o$ Number of output signals
* $n_s$ Number of samples in a signal
* $n_os$ Number of samples in an oversampled output signal
* $\mathbf{G}_{vv}$ CPSD matrix for the output signals
* $\mathbf{G}_{xx}$ CPSD matrix for the responses (i.e. the specification)
* $\mathbf{H}_{xv}$ Transfer function matrix between the responses and the output signals
* $\mathbf{X}$ Response spectra (FFT)
* $\mathbf{V}$ Output spectra (FFT)
* $\mathbf{T}$ Transformation matrix
* $\mathbf{A}$ State or system matrix for state space equations of motion
* $\mathbf{B}$ Input matrix for state space equations of motion
* $\mathbf{C}$ Output matrix for state space equations of motion
* $\mathbf{D}$ Feedthrough or feedforward matrix for state space equations of motion
* $\mathbf{x}$ State vector for state space equations of motion
* $\mathbf{y}$ Output vector for state space equations of motion
* $\mathbf{u}$ Input vector for state space equations of motion
* $\mathbf{M}$ Mass matrix for 2nd-order differential equations of motion
* $\mathbf{C}$ Damping matrix for 2nd-order differential equations of motion
* $\mathbf{K}$ Stiffness matrix for 2nd-order differential equations of motion

### Operations

To come.
