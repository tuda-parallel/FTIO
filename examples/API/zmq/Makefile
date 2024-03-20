all: test test_mpi test_mpi_struct

test: test.cpp
	g++ -o test test.cpp -I/d/github/TMIO/dep/msgpack/msgpack-c/include -lzmq

run_test: test
	./test

test_mpi: test_mpi.cxx
	mpicxx -o test_mpi test_mpi.cxx -I/d/github/TMIO/dep/msgpack/msgpack-c/include -lzmq

run_mpi: test_mpi
	mpirun -np 6 ./test_mpi

run_single_mpi: test_mpi
	mpirun -np 1 ./test_mpi

mpi: test_mpi run_mpi

test_mpi_struct: test_mpi_struct.cxx
	mpicxx -o test_mpi_struct test_mpi_struct.cxx -I/d/github/TMIO/dep/msgpack/msgpack-c/include -lzmq

run_mpi_struct: test_mpi_struct
	mpirun -np 6 ./test_mpi_struct

run_single_mpi_struct: test_mpi_struct
	mpirun -np 1 ./test_mpi_struct

mpi: test_mpi_struct run_mpi_struct

clean: 
	rm -f test test_mpi test_mpi_struct
