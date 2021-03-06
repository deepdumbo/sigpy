import numpy as np
import numba as nb

from sigpy import backend, config, util


__all__ = ['array_to_blocks', 'blocks_to_array']


def array_to_blocks(input, blk_shape, blk_strides):
    """
    output - num_blks + blk_shape
    """
    ndim = input.ndim

    if ndim != len(blk_shape) or ndim != len(blk_strides):
        raise ValueError('Input must have same dimensions as blocks.')

    num_blks = [(i - b + s) // s for i, b, s in zip(input.shape, blk_shape, blk_strides)]
    device = backend.get_device(input)
    xp = device.xp
    with device:
        output = xp.zeros(num_blks + blk_shape, dtype=input.dtype)
    
        if ndim == 1:
            if device == backend.cpu_device:
                _array_to_blocks1(output, input,
                                  blk_shape[-1],
                                  blk_strides[-1],
                                  num_blks[-1])
            else:
                _array_to_blocks1_cuda(output, input,
                                       blk_shape[-1],
                                       blk_strides[-1],
                                       num_blks[-1],
                                       size=num_blks[-1] * blk_shape[-1])
        elif ndim == 2:
            if device == backend.cpu_device:
                _array_to_blocks2(output, input,
                                  blk_shape[-1], blk_shape[-2],
                                  blk_strides[-1], blk_strides[-2],
                                  num_blks[-1], num_blks[-2])
            else:
                _array_to_blocks2_cuda(output, input,
                                       blk_shape[-1], blk_shape[-2],
                                       blk_strides[-1], blk_strides[-2],
                                       num_blks[-1], num_blks[-2],
                                       size=num_blks[-1] * num_blks[-2] * blk_shape[-1] * blk_shape[-2])
        elif ndim == 3:
            if device == backend.cpu_device:
                _array_to_blocks3(output, input,
                                  blk_shape[-1], blk_shape[-2], blk_shape[-3],
                                  blk_strides[-1], blk_strides[-2], blk_strides[-3],
                                  num_blks[-1], num_blks[-2], num_blks[-3])
            else:
                _array_to_blocks3_cuda(output, input,
                                       blk_shape[-1], blk_shape[-2], blk_shape[-3],
                                       blk_strides[-1], blk_strides[-2], blk_strides[-3],
                                       num_blks[-1], num_blks[-2], num_blks[-3],
                                       size=num_blks[-1] * num_blks[-2] * num_blks[-3] * blk_shape[-1] * blk_shape[-2] * blk_shape[-3])

        return output


def blocks_to_array(input, oshape, blk_shape, blk_strides):
    """
    output - num_blks + blk_shape
    """
    ndim = len(blk_shape)

    if 2 * ndim != input.ndim or ndim != len(blk_strides):
        raise ValueError('Input must have same dimensions as blocks.')
    
    num_blks = input.shape[:ndim]
    device = backend.get_device(input)
    xp = device.xp
    with device:
        output = xp.zeros(oshape, dtype=input.dtype)

        if ndim == 1:
            if device == backend.cpu_device:
                _blocks_to_array1(output, input,
                                  blk_shape[-1],
                                  blk_strides[-1],
                                  num_blks[-1])
            else:
                if np.issubdtype(input.dtype, np.floating):
                    _blocks_to_array1_cuda(output, input,
                                           blk_shape[-1],
                                           blk_strides[-1],
                                           num_blks[-1],
                                           size=num_blks[-1] * blk_shape[-1])
                else:
                    _blocks_to_array1_cuda_complex(output, input,
                                                   blk_shape[-1],
                                                   blk_strides[-1],
                                                   num_blks[-1],
                                                   size=num_blks[-1] * blk_shape[-1])
        elif ndim == 2:
            if device == backend.cpu_device:
                _blocks_to_array2(output, input,
                                  blk_shape[-1], blk_shape[-2],
                                  blk_strides[-1], blk_strides[-2],
                                  num_blks[-1], num_blks[-2])
            else:
                if np.issubdtype(input.dtype, np.floating):
                    _blocks_to_array2_cuda(output, input,
                                           blk_shape[-1], blk_shape[-2],
                                           blk_strides[-1], blk_strides[-2],
                                           num_blks[-1], num_blks[-2],
                                           size=num_blks[-1] * num_blks[-2] * blk_shape[-1] * blk_shape[-2])
                else:
                    _blocks_to_array2_cuda_complex(output, input,
                                                   blk_shape[-1], blk_shape[-2],
                                                   blk_strides[-1], blk_strides[-2],
                                                   num_blks[-1], num_blks[-2],
                                                   size=num_blks[-1] * num_blks[-2] * blk_shape[-1] * blk_shape[-2])
        elif ndim == 3:
            if device == backend.cpu_device:
                _blocks_to_array3(output, input,
                                  blk_shape[-1], blk_shape[-2], blk_shape[-3],
                                  blk_strides[-1], blk_strides[-2], blk_strides[-3],
                                  num_blks[-1], num_blks[-2], num_blks[-3])
            else:
                if np.issubdtype(input.dtype, np.floating):
                    _blocks_to_array3_cuda(output, input,
                                           blk_shape[-1], blk_shape[-2], blk_shape[-3],
                                           blk_strides[-1], blk_strides[-2], blk_strides[-3],
                                           num_blks[-1], num_blks[-2], num_blks[-3],
                                           size=num_blks[-1] * num_blks[-2] * num_blks[-3] * blk_shape[-1] * blk_shape[-2] * blk_shape[-3])
                else:
                    _blocks_to_array3_cuda_complex(output, input,
                                                   blk_shape[-1], blk_shape[-2], blk_shape[-3],
                                                   blk_strides[-1], blk_strides[-2], blk_strides[-3],
                                                   num_blks[-1], num_blks[-2], num_blks[-3],
                                                   size=num_blks[-1] * num_blks[-2] * num_blks[-3] * blk_shape[-1] * blk_shape[-2] * blk_shape[-3])

        return output


@nb.jit(nopython=True, cache=True)
def _array_to_blocks1(output, input, Bx, Sx, Nx):
    ndim = input.ndim
    
    for nx in range(Nx):
        for bx in range(Bx):
            ix = nx * Sx + bx
            if ix < input.shape[-1]:
                output[nx, bx] = input[ix]


@nb.jit(nopython=True, cache=True)
def _array_to_blocks2(output, input, Bx, By, Sx, Sy, Nx, Ny):
    ndim = input.ndim
    
    for ny in range(Ny):
        for nx in range(Nx):
            for by in range(By):
                for bx in range(Bx):
                    iy = ny * Sy + by
                    ix = nx * Sx + bx
                    if ix < input.shape[-1] and iy < input.shape[-2]:
                        output[ny, nx, by, bx] = input[iy, ix]


@nb.jit(nopython=True, cache=True)
def _array_to_blocks3(output, input, Bx, By, Bz, Sx, Sy, Sz, Nx, Ny, Nz):
    ndim = input.ndim

    for nz in range(Nz):
        for ny in range(Ny):
            for nx in range(Nx):
                for bz in range(Bz):
                    for by in range(By):
                        for bx in range(Bx):
                            iz = nz * Sz + bz
                            iy = ny * Sy + by
                            ix = nx * Sx + bx
                            if ix < input.shape[-1] and iy < input.shape[-2] and iz < input.shape[-3]:
                                output[nz, ny, nx, bz, by, bx] = input[iz, iy, ix]


@nb.jit(nopython=True, cache=True)
def _blocks_to_array1(output, input, Bx, Sx, Nx):
    ndim = output.ndim
    
    for nx in range(Nx):
        for bx in range(Bx):
            ix = nx * Sx + bx
            if ix < output.shape[-1]:
                output[ix] += input[nx, bx]


@nb.jit(nopython=True, cache=True)
def _blocks_to_array2(output, input, Bx, By, Sx, Sy, Nx, Ny):
    ndim = output.ndim
    
    for ny in range(Ny):
        for nx in range(Nx):
            for by in range(By):
                for bx in range(Bx):
                    iy = ny * Sy + by
                    ix = nx * Sx + bx
                    if ix < output.shape[-1] and iy < output.shape[-2]:
                        output[iy, ix] += input[ny, nx, by, bx]


@nb.jit(nopython=True, cache=True)
def _blocks_to_array3(output, input, Bx, By, Bz, Sx, Sy, Sz, Nx, Ny, Nz):
    ndim = output.ndim
    
    for nz in range(Nz):
        for ny in range(Ny):
            for nx in range(Nx):
                for bz in range(Bz):
                    for by in range(By):
                        for bx in range(Bx):
                            iz = nz * Sz + bz
                            iy = ny * Sy + by
                            ix = nx * Sx + bx
                            if ix < output.shape[-1] and iy < output.shape[-2] and iz < output.shape[-3]:
                                output[iz, iy, ix] += input[nz, ny, nx, bz, by, bx]


if config.cupy_enabled:
    import cupy as cp

    _array_to_blocks1_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 Sx, int32 Nx',
        '',
        """
        const int ndim = input.ndim;

        int nx = i / Bx;
        i -= nx * Bx;
        int bx = i;

        int ix = nx * Sx + bx;
        if (ix < input.shape()[ndim - 1]) {
            int input_idx[] = {ix};
            int output_idx[] = {nx, bx};
            output[output_idx] = input[input_idx];
        }
        """,
        name='_array_to_blocks1_cuda')

    _array_to_blocks2_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Sx, int32 Sy, int32 Nx, int32 Ny',
        '',
        """
        const int ndim = input.ndim;

        int ny = i / Bx / By / Nx;
        i -= ny * Bx * By * Nx;
        int nx = i / Bx / By;
        i -= nx * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < input.shape()[ndim - 1] && iy < input.shape()[ndim - 2]) {
            int input_idx[] = {iy, ix};
            int output_idx[] = {ny, nx, by, bx};
            output[output_idx] = input[input_idx];
        }
        """,
        name='_array_to_blocks2_cuda')

    _array_to_blocks3_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Bz, int32 Sx, int32 Sy, int32 Sz, int32 Nx, int32 Ny, int32 Nz',
        '',
        """
        const int ndim = input.ndim;

        int nz = i / Bx / By / Bz / Nx / Ny;
        i -= nz * Bx * By * Bz * Nx * Ny;
        int ny = i / Bx / By / Bz / Nx;
        i -= ny * Bx * By * Bz * Nx;
        int nx = i / Bx / By / Bz;
        i -= nx * Bx * By * Bz;
        int bz = i / Bx / By;
        i -= bz * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iz = nz * Sz + bz;
        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < input.shape()[ndim - 1] && iy < input.shape()[ndim - 2] && iz < input.shape()[ndim - 3]) {
            int input_idx[] = {iz, iy, ix};
            int output_idx[] = {nz, ny, nx, bz, by, bx};
            output[output_idx] = input[input_idx];
        }
        """,
        name='_array_to_blocks3_cuda')

    _blocks_to_array1_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 Sx, int32 Nx',
        '',
        """
        const int ndim = output.ndim;

        int nx = i / Bx;
        i -= nx * Bx;
        int bx = i;

        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1]) {
            int input_idx[] = {nx, bx};
            int output_idx[] = {ix};
            atomicAdd(&output[output_idx], input[input_idx]);
        }
        """,
        name='_blocks_to_array1_cuda')


    _blocks_to_array1_cuda_complex = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 Sx, int32 Nx',
        '',
        """
        const int ndim = output.ndim;

        int nx = i / Bx;
        i -= nx * Bx;
        int bx = i;

        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1]) {
            int input_idx[] = {nx, bx};
            int output_idx[] = {ix};
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])), input[input_idx].real());
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])) + 1, input[input_idx].imag());
        }
        """,
        name='_blocks_to_array1_cuda_complex')
    

    _blocks_to_array2_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Sx, int32 Sy, int32 Nx, int32 Ny',
        '',
        """
        const int ndim = output.ndim;

        int ny = i / Bx / By / Nx;
        i -= ny * Bx * By * Nx;
        int nx = i / Bx / By;
        i -= nx * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1] && iy < output.shape()[ndim - 2]) {
            int input_idx[] = {ny, nx, by, bx};
            int output_idx[] = {iy, ix};
            atomicAdd(&output[output_idx], input[input_idx]);
        }
        """,
        name='_blocks_to_array2_cuda')
    

    _blocks_to_array2_cuda_complex = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Sx, int32 Sy, int32 Nx, int32 Ny',
        '',
        """
        const int ndim = output.ndim;

        int ny = i / Bx / By / Nx;
        i -= ny * Bx * By * Nx;
        int nx = i / Bx / By;
        i -= nx * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1] && iy < output.shape()[ndim - 2]) {
            int input_idx[] = {ny, nx, by, bx};
            int output_idx[] = {iy, ix};
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])), input[input_idx].real());
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])) + 1, input[input_idx].imag());
        }
        """,
        name='_blocks_to_array2_cuda_complex')


    _blocks_to_array3_cuda = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Bz, int32 Sx, int32 Sy, int32 Sz, int32 Nx, int32 Ny, int32 Nz',
        '',
        """
        const int ndim = output.ndim;

        int nz = i / Bx / By / Bz / Nx / Ny;
        i -= nz * Bx * By * Bz * Nx * Ny;
        int ny = i / Bx / By / Bz / Nx;
        i -= ny * Bx * By * Bz * Nx;
        int nx = i / Bx / By / Bz;
        i -= nx * Bx * By * Bz;
        int bz = i / Bx / By;
        i -= bz * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iz = nz * Sz + bz;
        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1] && iy < output.shape()[ndim - 2] && iz < output.shape()[ndim - 3]) {
            int input_idx[] = {nz, ny, nx, bz, by, bx};
            int output_idx[] = {iz, iy, ix};
            atomicAdd(&output[output_idx], input[input_idx]);
        }
        """,
        name='_blocks_to_array3_cuda')


    _blocks_to_array3_cuda_complex = cp.ElementwiseKernel(
        'raw T output, raw T input, int32 Bx, int32 By, int32 Bz, int32 Sx, int32 Sy, int32 Sz, int32 Nx, int32 Ny, int32 Nz',
        '',
        """
        const int ndim = output.ndim;

        int nz = i / Bx / By / Bz / Nx / Ny;
        i -= nz * Bx * By * Bz * Nx * Ny;
        int ny = i / Bx / By / Bz / Nx;
        i -= ny * Bx * By * Bz * Nx;
        int nx = i / Bx / By / Bz;
        i -= nx * Bx * By * Bz;
        int bz = i / Bx / By;
        i -= bz * Bx * By;
        int by = i / Bx;
        i -= by * Bx;
        int bx = i;

        int iz = nz * Sz + bz;
        int iy = ny * Sy + by;
        int ix = nx * Sx + bx;
        if (ix < output.shape()[ndim - 1] && iy < output.shape()[ndim - 2] && iz < output.shape()[ndim - 3]) {
            int input_idx[] = {nz, ny, nx, bz, by, bx};
            int output_idx[] = {iz, iy, ix};
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])), input[input_idx].real());
            atomicAdd(reinterpret_cast<T::value_type*>(&(output[output_idx])) + 1, input[input_idx].imag());
        }
        """,
        name='_blocks_to_array3_cuda_complex')

