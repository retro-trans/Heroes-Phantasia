#include <fstream>
#include <iterator>
#include <vector>
#include <iostream>
#include "PrxDecrypter.h"
extern "C" {
#include "libkirk/kirk_engine.h"
}
int main(int argc, char **argv) {
    if (argc != 3) { std::cerr << "Usage: decrypt_game INPUT OUTPUT\n"; return 2; }
    std::ifstream in(argv[1], std::ios::binary);
    if (!in) return 3;
    std::vector<u8> src((std::istreambuf_iterator<char>(in)), {});
    if (src.size() < 0x150 || src.size() > 0x7fffffff) return 4;
    if (src[0] != '~' || src[1] != 'P' || src[2] != 'S' || src[3] != 'P') return 5;
    if (src[6] != 0 || src[7] != 0) { std::cerr << "Compressed input unsupported by this driver\n"; return 6; }
    std::vector<u8> dst(src.size());
    kirk_init();
    int n = pspDecryptPRX(src.data(), dst.data(), src.size(), nullptr, true);
    std::cout << "Decrypted bytes: " << n << "\n";
    if (n < 4 || dst[0] != 0x7f || dst[1] != 'E' || dst[2] != 'L' || dst[3] != 'F') return 7;
    std::ifstream existing(argv[2], std::ios::binary);
    if (existing) { std::cerr << "Refusing overwrite\n"; return 8; }
    std::ofstream out(argv[2], std::ios::binary);
    out.write(reinterpret_cast<char *>(dst.data()), n);
    return out ? 0 : 9;
}
