// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AXI Wisdom Vault
 * @author The Architect (ENVOLVERON)
 * @notice A legacy contract to store Actual_Extra_Intelligence concepts as eternal artifacts.
 * @dev Uses ERC721 for uniqueness. Metadata MUST be stored on Arweave for 100+ year persistence.
 */

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract AXILegacyVault is ERC721, ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIdCounter;

    // The AXI Concept Structure
    struct AXIConcept {
        string name;            // e.g., "Nameration"
        string category;        // e.g., "Extra_Ability"
        uint256 creationDate;   // Timestamp
        string arweaveLink;     // Link to the full Video/Audio/Text package
    }

    mapping(uint256 => AXIConcept) public concepts;

    // Events to signal to the future that wisdom has been logged
    event WisdomMinted(uint256 indexed tokenId, string name, string arweaveLink);

    constructor(address initialOwner) 
        ERC721("AXI Wisdom Archive", "AXI") 
        Ownable(initialOwner) 
    {}

    /**
     * @dev Mints a new Concept as an NFT.
     * @param to The address receiving the wisdom (likely your cold wallet).
     * @param conceptName The name of the AXI concept.
     * @param category The classification (Voidz, Arbiter, etc.).
     * @param arweaveURI The permanent link to the content (metadata).
     */
    function preserveConcept(
        address to, 
        string memory conceptName, 
        string memory category,
        string memory arweaveURI
    ) public onlyOwner {
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        // Store the concept data on-chain (immutable record)
        concepts[tokenId] = AXIConcept({
            name: conceptName,
            category: category,
            creationDate: block.timestamp,
            arweaveLink: arweaveURI
        });

        _safeMint(to, tokenId);
        _setTokenURI(tokenId, arweaveURI);

        emit WisdomMinted(tokenId, conceptName, arweaveURI);
    }

    // Standard Overrides required by Solidity
    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
    
    /**
     * @dev Withdraw function. If people buy these in the future, 
     * this allows your great-grandchildren to access the funds.
     */
    function withdraw() public onlyOwner {
        uint256 balance = address(this).balance;
        payable(owner()).transfer(balance);
    }
}