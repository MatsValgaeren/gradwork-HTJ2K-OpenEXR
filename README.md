# Gradwork HTJ2K in OpenEXR

</div>

<details>
<summary>Table of Contents</summary>

- [About](#about)
- [Credits](#credits)
- [License](#license)

</details>


## About

This Repository contains my research about the new HTJ2K Compression method that recently got added to OpenEXR.
The scripts were used to test the de-/compression speed and file size of all lossless OpenEXR compression methods.

Research done as Grad Work @ [Howest](https://www.howest.be/en) - [DAE](https://www.digitalartsandentertainment.be/)

## Results (02/02/2026)

Currently, the OpenJPH implementation of High-Throughput JPEG 2000 does not outperform es-
tablished OpenEXR codecs (ZIP, ZIPS, PIZ) across compression ratio, compression speed, decom-
pression speed, or ROI decoding performance.

However, results indicate that HTJ2K requires only moderate optimization to become the superior
lossless compression method. More efficient (especially proprietary) algorithms can bridge the gap, as
they have already demonstrated multiple-fold performance gains.

Although improvements in decompression would benefit ROI and progressive decoding capabilities, compositing workflows require fast full-frame access over progressive loading.

For a more thorough understanding of my results: Read the GW2526_Valgaeren_Mats_HTJ2K-in-OpenEXR.pdf

## Credits

-   Script by Mats Valgaeren


## License

[GNU General Public License v3.0](LICENSE)
