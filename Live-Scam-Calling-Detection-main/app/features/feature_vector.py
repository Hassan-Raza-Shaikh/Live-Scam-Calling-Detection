class FeatureVectorAssembler:
    """Assembles all acoustic, linguistic, and behavioral feature maps into a single vector/dict."""
    def assemble(self, acoustic: dict, linguistic: dict, behavioral: dict) -> dict:
        merged = {}
        merged.update(acoustic)
        merged.update(linguistic)
        merged.update(behavioral)
        return merged
