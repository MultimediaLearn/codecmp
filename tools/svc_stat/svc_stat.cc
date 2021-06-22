#include <cstdio>
#include <cstring>
#include <cstdint>
#include <string>

int main(int argc, char *argv[]) {
    int ret = 0, log = 0;
    if (argc < 2) {
        fprintf(stderr, "Usage %s xx.h264 [drop_level]\n", argv[0]);
        return -1;
    }
    const char* kpH264FileName = argv[1];

    int sep = -1;
    if (argc >= 3) {
        sep = std::stoi(argv[2]);
    }

    FILE* pH264File   = NULL;
    int32_t iSliceSize;
  
    if (kpH264FileName) {
        pH264File = fopen (kpH264FileName, "rb");
        if (pH264File == NULL) {
            fprintf (stderr, "Can not open h264 source file, check its legal path related please..\n");
            return -1;
        }
        fprintf (stderr, "H264 source file name: [%s]\n", kpH264FileName);
    } else {
        fprintf (stderr, "Can not find any h264 bitstream file to read..\n");
        fprintf (stderr, "----------------decoder return------------------------\n");
        return -1;
    }
  
    fseek (pH264File, 0L, SEEK_END);
    int32_t iFileSize = (int32_t) ftell (pH264File);
    if (iFileSize <= 4) {
        fprintf (stderr, "Current Bit Stream File is too small, read error!!!!\n");
        return -1;
    }
    fseek (pH264File, 0L, SEEK_SET);  

    uint8_t *pBuf = new uint8_t[iFileSize + 4];
    if (pBuf == NULL) {
        fprintf (stderr, "new buffer failed!\n");
        return -1;
    }

    if (fread (pBuf, 1, iFileSize, pH264File) != (uint32_t)iFileSize) {
        fprintf (stderr, "Unable to read whole file\n");
        return -1;
    }
    
    uint8_t startCode[] = {0, 0, 0, 1};
    memcpy (pBuf + iFileSize, startCode, 4); //confirmed_safe_unsafe_usag
  
    FILE *sdfd = NULL;
    if (sep >= 0) {
        const std::string fpath = std::string("") + kpH264FileName + "_b" + std::to_string(sep) + ".264";
        sdfd = fopen(fpath.c_str(), "wb");
        if (!sdfd) {
            fprintf(stderr, "\033[32;1m %s open [%s] failed \033[0m\n", __FUNCTION__, fpath.c_str());
            return -1;
        }
        fprintf(stderr, "\033[32;1m %s open [%s] successed \033[0m\n", __FUNCTION__, fpath.c_str());
    }

    int32_t slice_ind = 0, i = 0;
    int32_t iBufStart = 0;          // start of NALU
    int32_t iBufPos = 0;            // start of NALU content
    uint8_t forbidden_zero = 0;
    uint8_t ref_idc = -1;
    uint8_t nal_type = 0;
    uint64_t size_level_0 = 0, size_level_1 = 0, size_level_2 = 0, size_level_3 = 0;
    while (true) {
        if (iBufPos >= iFileSize)
            break;

        int len_prefix = 3;
        for (i = 0; i < iFileSize; i++) {
            if (pBuf[iBufPos + i] == 0 && pBuf[iBufPos + i + 1] == 0 && pBuf[iBufPos + i + 2] == 0 && pBuf[iBufPos + i + 3] == 1) {
                len_prefix = 4;
                break;
            } else if (pBuf[iBufPos + i] == 0 && pBuf[iBufPos + i + 1] == 0 && pBuf[iBufPos + i + 2] == 1) {
                break;
            }
        }
        if (iBufPos != 0 && i < 4) {
            break;
        } else if (iBufPos == 0 && i != 0) {
            iBufPos = iBufStart = i;
            break;
        }

        iBufPos += i;
        if (i > 0 && sep >= 0 && (3 - ref_idc) <= sep) {
            // save previous NALU 
            fwrite(pBuf + iBufStart, (iBufPos - iBufStart), 1, sdfd);
        }
        iBufStart = iBufPos;
        iBufPos += len_prefix;

        slice_ind ++;
        switch (ref_idc) {
        case 3:
            size_level_0 += (i + len_prefix);
            break;
        case 2:
            size_level_1 += (i + len_prefix);
            break;
        case 1:
            size_level_2 += (i + len_prefix);
            break;
        case 0:
            size_level_3 += (i + len_prefix);
            break;
        default:
            break;
        }

        uint8_t nal_header = pBuf[iBufPos];
        forbidden_zero = !!(nal_header & 0x80);
        ref_idc = (nal_header & 0x60) >> 5;
        nal_type = nal_header & 0x1f;
        if (log) {
            fprintf(stderr, "%u: forbidden zero: %hu, ref_idc: %hu, nalu type: %hu\n",
                             slice_ind, forbidden_zero, ref_idc, nal_type);
        }
    }

    float total_size = size_level_0 + size_level_1 + size_level_2 + size_level_3;
    fprintf(stderr, "\033[32;1m"
                    "level 0: %lu(%.0f%) bytes \t level 1: %lu(%.0f%) bytes \t "
                    "level 2: %lu(%.0f%) bytes \t level 3: %lu(%.0f%) bytes\n"
                    "\033[0m",
                    size_level_0, size_level_0 / total_size * 100,
                    size_level_1, size_level_1 / total_size * 100,
                    size_level_2, size_level_2 / total_size * 100,
                    size_level_3, size_level_3 / total_size * 100);

    if (sdfd) fclose(sdfd);

    return 0;
}
